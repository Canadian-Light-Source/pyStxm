"""Tucsen areaDetector support using the ophyd 1.9 file-store interfaces.

Select HDF5 or TIFF and configure paths, filenames and frame counts BEFORE
staging. Unstage before changing formats, paths or acquisition geometry.
Only the selected file plugin is staged. The V22 plugin classes preserve the
original IOC interface; their version refers to ADCore, not ophyd.
The HDF5 plugin must have received a frame before its first stage. Call
prime_hdf5_plugin() explicitly before staging when safe for the hardware.
It acquires one Free Run frame without saving files and restores settings.

Each trigger produces one datum representing ``cam.num_images`` frames.
In external-trigger mode, trigger() arms the camera and its status waits for
the whole burst, not individual frames. Direct writes to cam.acquire bypass
datum generation. Changing directories during a staged hardware scan also
invalidates resource metadata: stage each scan segment separately instead.

Trigger completion follows the camera Acquire falling edge, as in ophyd's
SingleTrigger. It is not an independent guarantee of successful disk writes;
hardware scans must also check the IOC writer's completion/error signals.
"""

from datetime import datetime
from functools import partial
import math
import time

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
import numpy as np

from ophyd.areadetector.base import (
    ADComponent as ADCpt,
    EpicsSignalWithRBV as SignalWithRBV,
)
from ophyd.areadetector.cam import CamBase
from ophyd.areadetector.detectors import DetectorBase
from ophyd.areadetector.filestore_mixins import (
    FileStoreHDF5SingleIterativeWrite,
    FileStoreTIFFIterativeWrite,
    new_short_uid,
)
from ophyd.areadetector.plugins import (
    HDF5Plugin_V22,
    ImagePlugin,
    TIFFPlugin_V22,
)
from ophyd.areadetector.trigger_mixins import ADTriggerStatus, SingleTrigger
from ophyd.device import Staged
from ophyd.signal import EpicsSignalRO
from ophyd.utils.errors import RedundantStaging


IMG_FTYPE_HDF5 = 0
IMG_FTYPE_TIFF = 1
rootdir = "/opt/"
dest = "/opt/test_data/guest/0623/"


class _TucsenFileStoreMixin:
    """Keep plan-supplied names and use upstream resource/datum generation."""

    def make_filename(self):
        # An empty IOC filename gets a unique name, as in upstream ophyd.
        filename = self.file_name.get() or new_short_uid()
        formatter = datetime.now().strftime
        read_path = formatter(self.read_path_template)
        write_path = formatter(self.write_path_template)
        separator = "\\" if self.path_semantics == "windows" else "/"
        if not write_path.endswith(separator):
            write_path += separator
        return filename, read_path, write_path

    def stage(self):
        if self.parent is not None and hasattr(self.parent, "_file_plugin_name"):
            if self is not self.parent.file_plugin:
                return []
        super().stage()
        # The upstream file-store mixins do not forward Device.stage's list.
        return [self]

    def unstage(self):
        if self._staged == Staged.no:
            return []
        super().unstage()
        return [self]


class TUCSEN_TIFFPlugin(TIFFPlugin_V22):
    """TIFF interface for the original V22-compatible IOC."""


class TUCSEN_TIFFPluginWithFileStore(
    _TucsenFileStoreMixin, TUCSEN_TIFFPlugin, FileStoreTIFFIterativeWrite
):
    """One TIFF file per frame, grouped into one datum per acquisition."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.windows_write_path = ""


class TUCSEN_HDF5_Plugin(
    _TucsenFileStoreMixin, HDF5Plugin_V22, FileStoreHDF5SingleIterativeWrite
):
    """One HDF5 file per frame, grouped into one datum per acquisition."""


class TucsenDetectorCam(CamBase):
    _html_docs = []
    serial_number = ADCpt(EpicsSignalRO, "SerialNumber_RBV")
    firmware_version = ADCpt(EpicsSignalRO, "FirmwareVersion_RBV")
    sdk_version = ADCpt(EpicsSignalRO, "SDKVersion_RBV")
    bus = ADCpt(EpicsSignalRO, "Bus_RBV")
    driver_version = ADCpt(EpicsSignalRO, "DriverVersion_RBV")
    adcore_version = ADCpt(EpicsSignalRO, "ADCoreVersion_RBV")

    fan_gear = ADCpt(SignalWithRBV, "FanGear")
    auto_exposure = ADCpt(SignalWithRBV, "AutoExposure")
    histogram = ADCpt(SignalWithRBV, "Histogram")
    defect_correction = ADCpt(SignalWithRBV, "DefectCorrection")
    auto_levels = ADCpt(SignalWithRBV, "AutoLevels")
    enhance = ADCpt(SignalWithRBV, "Enhance")
    enable_denoise = ADCpt(SignalWithRBV, "EnableDenoise")
    dyn_rge_correction = ADCpt(SignalWithRBV, "DynRgeCorrection")
    gamma = ADCpt(SignalWithRBV, "Gamma")
    contrast = ADCpt(SignalWithRBV, "Contrast")
    hdrk = ADCpt(SignalWithRBV, "HDRK")
    left_levels = ADCpt(SignalWithRBV, "LeftLevels")
    right_levels = ADCpt(SignalWithRBV, "RightLevels")
    black_level = ADCpt(SignalWithRBV, "BlackLevel")
    brightness = ADCpt(SignalWithRBV, "Brightness")
    sharpness = ADCpt(SignalWithRBV, "Sharpness")
    noise_level = ADCpt(SignalWithRBV, "NoiseLevel")

    trigger_exposure = ADCpt(SignalWithRBV, "TriggerExposure")
    trigger_edge = ADCpt(SignalWithRBV, "TriggerEdge")
    trigger_delay = ADCpt(SignalWithRBV, "TriggerDelay")

    trigger_out_1_mode = ADCpt(SignalWithRBV, "TriggerOut1Mode")
    trigger_out_1_edge = ADCpt(SignalWithRBV, "TriggerOut1Edge")
    trigger_out_1_delay = ADCpt(SignalWithRBV, "TriggerOut1Delay")
    trigger_out_1_width = ADCpt(SignalWithRBV, "TriggerOut1Width")
    trigger_out_2_mode = ADCpt(SignalWithRBV, "TriggerOut2Mode")
    trigger_out_2_edge = ADCpt(SignalWithRBV, "TriggerOut2Edge")
    trigger_out_2_delay = ADCpt(SignalWithRBV, "TriggerOut2Delay")
    trigger_out_2_width = ADCpt(SignalWithRBV, "TriggerOut2Width")
    trigger_out_3_mode = ADCpt(SignalWithRBV, "TriggerOut3Mode")
    trigger_out_3_edge = ADCpt(SignalWithRBV, "TriggerOut3Edge")
    trigger_out_3_delay = ADCpt(SignalWithRBV, "TriggerOut3Delay")
    trigger_out_3_width = ADCpt(SignalWithRBV, "TriggerOut3Width")

    def dump_report(self):
        """Report identification and already-instantiated camera signals."""
        for label, attribute in (
            ("Manufacturer", "manufacturer"),
            ("Model", "model"),
            ("Serial Number", "serial_number"),
            ("Firmware Version", "firmware_version"),
            ("SDK Version", "sdk_version"),
            ("Bus", "bus"),
            ("Driver Version", "driver_version"),
            ("ADCore Version", "adcore_version"),
        ):
            print(f"{label}: {getattr(self, attribute).get()}")
        for walk in self.walk_signals(include_lazy=False):
            print(f"\t{walk.dotted_name} = {walk.item.get()}")


class TucsenDetector(SingleTrigger, DetectorBase):
    """Finite software acquisitions or externally triggered frame bursts.

    acquisition_timeout is in seconds and includes waiting for external
    triggers. Set it longer than the longest expected burst. File-store
    retrieval requires AD_TIFF and AD_HDF5_SINGLE handlers in the data reader.
    """

    _html_docs = []
    cam = ADCpt(TucsenDetectorCam, "cam1:")
    image = ADCpt(ImagePlugin, "image1:")
    tif_file_plugin = ADCpt(
        TUCSEN_TIFFPluginWithFileStore,
        "TIFF1:",
        write_path_template=dest,
        read_path_template=dest,
        read_attrs=[],
        root=rootdir,
    )
    hdf5_file_plugin = ADCpt(
        TUCSEN_HDF5_Plugin,
        "HDF1:",
        write_path_template=dest,
        read_path_template=dest,
        read_attrs=[],
        root=rootdir,
    )

    def __init__(self, prefix, name, *, acquisition_timeout=60.0, **kwargs):
        if not math.isfinite(acquisition_timeout) or acquisition_timeout <= 0:
            raise ValueError("acquisition_timeout must be finite and positive")
        self._file_plugin_name = "hdf5_file_plugin"
        super().__init__(prefix=prefix, name=name, **kwargs)
        self._status_type = partial(ADTriggerStatus, timeout=acquisition_timeout)
        # Preserve the caller's single/multiple mode, including hardware bursts.
        self.stage_sigs.pop("cam.image_mode", None)
        self.read_attrs = [self._file_plugin_name]
        self._configure_file_plugins()

    @property
    def file_plugin(self):
        """The selected writer (also supports callers using file_plugin)."""
        return getattr(self, self._file_plugin_name)

    def _configure_file_plugins(self):
        for name in ("hdf5_file_plugin", "tif_file_plugin"):
            plugin = getattr(self, name)
            enabled = name == self._file_plugin_name
            plugin.stage_sigs["enable"] = int(enabled)
            # Disable the inactive writer before any child is staged.
            self.stage_sigs[f"{name}.enable"] = int(enabled)
        self.read_attrs = [self._file_plugin_name]

    def enable_file_plugin_by_name(self, nm="HDF5"):
        """Select a writer before staging; reselecting the same one is safe."""
        normalized = nm.upper()
        if "HDF5" in normalized:
            selected = "hdf5_file_plugin"
        elif "TIFF" in normalized or normalized == "TIF":
            selected = "tif_file_plugin"
        else:
            raise ValueError(f"Unknown file format {nm!r}; use HDF5 or TIFF")
        if self._staged != Staged.no:
            if selected != self._file_plugin_name:
                raise RuntimeError("Unstage the detector before changing file format")
            return
        self._file_plugin_name = selected
        self._configure_file_plugins()
        for name in ("hdf5_file_plugin", "tif_file_plugin"):
            getattr(self, name).enable.set(int(name == selected)).wait()

    def stage(self):
        if self._staged != Staged.no:
            raise RedundantStaging("Unstage the detector before staging again")
        if self.cam.image_mode.get() not in (0, 1, "Single", "Multiple"):
            raise ValueError("Use Single or Multiple image mode, not Continuous")
        frames = self.cam.num_images.get()
        if frames < 1:
            raise ValueError("cam.num_images must be positive")
        if self.cam.image_mode.get() in (0, "Single") and frames != 1:
            raise ValueError("Single image mode requires cam.num_images = 1")
        self._configure_file_plugins()
        super().stage()
        return [self] + [
            getattr(self, name)
            for name in self._sub_devices
            if getattr(self, name)._staged == Staged.yes
        ]

    def prime_hdf5_plugin(self, timeout=10.0):
        """Prime an empty HDF5 plugin without writing files or staging.

        This takes one real camera exposure. Existing array metadata makes
        this a no-op; an active acquisition or capture is never interrupted.
        """
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        if self._staged != Staged.no:
            raise RuntimeError("Unstage the detector before priming HDF5")
        plugin = self.hdf5_file_plugin
        if np.array(plugin.array_size.get()).sum() != 0:
            return
        if self.cam.acquire.get() != 0:
            raise RuntimeError("Cannot prime HDF5 while the camera is acquiring")
        writers = (self.hdf5_file_plugin, self.tif_file_plugin)
        if any(writer.capture.get() != 0 for writer in writers):
            raise RuntimeError("Cannot prime HDF5 while a file plugin is capturing")

        camera_settings = [
            (self.cam.array_callbacks, 1),
            (self.cam.image_mode, 0),  # Single
            (self.cam.num_images, 1),
            (self.cam.trigger_mode, 0),  # Tucsen Free Run, not "Internal"
            (self.cam.acquire_time, 0.1),
            (self.cam.acquire_period, 0.102),
        ]
        writer_settings = [
            (writer.auto_save, 0) for writer in writers
        ] + [
            (writer.enable, int(writer is plugin)) for writer in writers
        ]
        settings = writer_settings + camera_settings
        original_values = [(signal, signal.get()) for signal, _ in settings]
        try:
            for signal, value in settings:
                signal.set(value).wait(timeout=timeout)
            deadline = time.monotonic() + timeout
            self.cam.acquire.set(1).wait(timeout=timeout)
            while (
                self.cam.acquire.get() != 0
                or np.array(plugin.array_size.get()).sum() == 0
            ):
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"HDF5 priming for {self.name} did not complete within "
                        f"{timeout} seconds; check camera acquisition, array "
                        "callbacks and the HDF5 NDArrayPort"
                    )
                time.sleep(0.01)
        finally:
            # Stop before restoring auto-save so the priming frame is not saved.
            self.cam.acquire.set(0).wait(timeout=timeout)
            for signal, value in reversed(original_values):
                signal.set(value).wait(timeout=timeout)

    def trigger(self):
        """Arm one acquisition and generate its file-store datum."""
        if self._staged != Staged.yes:
            raise RuntimeError("Stage the detector before triggering")
        if self._status is not None and not self._status.done:
            raise RuntimeError("An acquisition is already in progress")
        if self.cam.acquire.get() != 0:
            raise RuntimeError("The camera is already acquiring")
        plugin = self.file_plugin
        # EnableCallbacks is string=True; ophyd may coerce even numeric reads.
        enabled = plugin.enable.get(use_monitor=False)
        if enabled not in (1, "1", "Enable"):
            raise RuntimeError(
                f"The selected file plugin {plugin.dotted_name} is disabled "
                f"(EnableCallbacks readback: {enabled!r})"
            )
        return super().trigger()

    def generate_datum(self, key, timestamp, datum_kwargs=None):
        """Route image references only to the writer staged for this run."""
        return self.file_plugin.generate_datum(key, timestamp, datum_kwargs)

    def _acquire_changed(self, value=None, old_value=None, **kwargs):
        if self._status is not None and self._status.done:
            self._status = None
        super()._acquire_changed(value=value, old_value=old_value, **kwargs)

    def stop(self, *, success=False):
        """Stop acquisition, including after an external-trigger timeout."""
        status, self._status = self._status, None
        if status is not None and not status.done:
            if success:
                status.set_finished()
            else:
                status.set_exception(RuntimeError("Tucsen acquisition was stopped"))
        self.cam.acquire.set(0).wait()
        super().stop(success=success)

    def unstage(self):
        children = [
            getattr(self, name)
            for name in self._sub_devices
            if getattr(self, name)._staged != Staged.no
        ]
        if self._staged != Staged.no:
            self.stop()
        super().unstage()
        return children + [self]

    def set_dwell(self, dwell_ms):
        """Set exposure in milliseconds, with a 2 ms period margin."""
        if not math.isfinite(dwell_ms) or dwell_ms <= 0:
            raise ValueError("dwell_ms must be finite and positive")
        dwell_sec = dwell_ms * 0.001
        self.cam.acquire_time.set(dwell_sec).wait()
        self.cam.acquire_period.set(dwell_sec + 0.002).wait()

    def get_name(self):
        return self.name

    def get_position(self):
        return 0.0

    def get_temperature(self):
        return self.cam.temperature_actual.get()

    def set_trigger_mode_hdw_trig(self):
        """Select Standard external triggering on the Dhyana 95 V2."""
        self.set_trigger_signal(1)

    def set_trigger_signal(self, mode):
        """Set the IOC trigger-mode enum (0=Free Run, 1=Standard)."""
        self.cam.trigger_mode.set(mode).wait()

    def set_file_output_path(self, cam_root_dir, fpath, *, read_path=None):
        """Configure both writers before staging.

        fpath is the IOC directory. read_path is its client-visible mapping,
        defaulting to fpath. Despite the legacy argument name, cam_root_dir
        must be the client-visible resource root containing read_path.
        """
        if self._staged != Staged.no:
            raise RuntimeError("Unstage the detector before changing output paths")
        for plugin in (self.hdf5_file_plugin, self.tif_file_plugin):
            plugin.reg_root = cam_root_dir
            plugin.read_path_template = fpath if read_path is None else read_path
            plugin.write_path_template = fpath
            # Validate client-side paths now; the IOC checks write paths at stage.
            _ = plugin.read_path_template


def make_scan_plan(motor1, motor2, motor3, motor4, noisy_det, tucsen, md=None):
    """Example software-triggered scan with exception-safe stage/unstage."""
    data_dir = f"{dest.rstrip('/')}/C{new_short_uid()}/"
    tucsen.enable_file_plugin_by_name("HDF5")
    tucsen.set_file_output_path(rootdir, data_dir)
    yield from bps.mv(
        tucsen.cam.image_mode, 0,
        tucsen.cam.num_images, 1,
        tucsen.cam.trigger_mode, 0,
        tucsen.cam.acquire_time, 0.3,
        tucsen.cam.acquire_period, 0.302,
    )

    @bpp.stage_decorator([tucsen])
    @bpp.run_decorator(md=md)
    def do_scan():
        for outer in np.linspace(0, 10, 2):
            yield from bps.mv(motor3, outer)
            for inner in np.linspace(-15, 15, 3):
                yield from bps.mv(motor4, inner)
                for y in np.linspace(-5, 5, 4):
                    yield from bps.mv(motor2, y)
                    for x in np.linspace(-5, 5, 4):
                        yield from bps.mv(motor1, x)
                        yield from bps.trigger_and_read(
                            [tucsen, noisy_det, motor2, motor1]
                        )

    return (yield from do_scan())
