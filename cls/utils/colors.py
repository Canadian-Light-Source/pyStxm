from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


class ColorsObject(object):
    """
    tis class is meant to be the single instance that is used by the main app for detector signals and by the
    camera plotter so that both can pull colors from a master object and keep the colors unigue as they are
    used
    """

    def __init__(self):
        super(ColorsObject, self).__init__()
        self.color_map = {}
        self._color_keys = []
        self._color_idxs = []
        self._used_colors = []
        self._used_idxs = []
        self._color_idx = 0
        self.reset_color_map()

    def reset_color_map(self):
        self.color_map = {}
        self.color_map.update(mcolors.TABLEAU_COLORS)
        self.color_map.update(mcolors.CSS4_COLORS)
        # remove black because the font that shopws name is also black
        self.color_map.pop("black")
        self._color_keys = list(self.color_map.keys())
        self._color_idxs = list(range(len(self.color_map)))
        self._used_colors = []
        self._used_idxs = []
        self._color_idx = 0

    def get_next_color(self):
        # grab the next color in master list
        clr = self._color_keys.pop(0)
        nxt_clr = self.color_map.pop(clr)
        return (clr, nxt_clr)

    def plot_colortable(colors, title, sort_colors=False, emptycols=0):
        """
        a function to demo the colors
        """

        cell_width = 212
        cell_height = 22
        swatch_width = 48
        margin = 12
        topmargin = 40

        # Sort colors by hue, saturation, value and name.
        if sort_colors is True:
            by_hsv = sorted(
                (tuple(mcolors.rgb_to_hsv(mcolors.to_rgb(color))), name)
                for name, color in colors.items()
            )
            names = [name for hsv, name in by_hsv]
        else:
            names = list(colors)

        n = len(names)
        ncols = 4 - emptycols
        nrows = n // ncols + int(n % ncols > 0)

        width = cell_width * 4 + 2 * margin
        height = cell_height * nrows + margin + topmargin
        dpi = 72

        fig, ax = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)
        fig.subplots_adjust(
            margin / width,
            margin / height,
            (width - margin) / width,
            (height - topmargin) / height,
        )
        ax.set_xlim(0, cell_width * 4)
        ax.set_ylim(cell_height * (nrows - 0.5), -cell_height / 2.0)
        ax.yaxis.set_visible(False)
        ax.xaxis.set_visible(False)
        ax.set_axis_off()
        ax.set_title(title, fontsize=24, loc="left", pad=10)

        for i, name in enumerate(names):
            row = i % nrows
            col = i // nrows
            y = row * cell_height

            swatch_start_x = cell_width * col
            text_pos_x = cell_width * col + swatch_width + 7

            ax.text(
                text_pos_x,
                y,
                name,
                fontsize=14,
                horizontalalignment="left",
                verticalalignment="center",
            )

            ax.add_patch(
                Rectangle(
                    xy=(swatch_start_x, y - 9),
                    width=swatch_width,
                    height=18,
                    facecolor=colors[name],
                    edgecolor="0.7",
                )
            )

        return fig


if __name__ == "__main__":
    clr_obj = ColorsObject()
    i = 0
    for i in range(50):
        c = clr_obj.get_next_color()
        print(f"[{i}] c = {c}")

    print("whats left")
    i = 0
    for c in clr_obj.color_map.items():
        print(f"[{i}] c = {c}")
        i += 1

    print("after reset whats left")
    i = 0
    clr_obj.reset_color_map()
    for c in clr_obj.color_map.items():
        print(f"[{i}] c = {c}")
        i += 1
