import cv2
import os

# def create_video_from_images(image_folder, output_video_path, fps=25):
#     images = sorted([img for img in os.listdir(image_folder) if img.endswith(".tiff")])
#     frame = cv2.imread(os.path.join(image_folder, images[0]))
#     height, width, _ = frame.shape
#     video_writer = cv2.VideoWriter(output_video_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
#
#     for image in images:
#         img_path = os.path.join(image_folder, image)
#         frame = cv2.imread(img_path)
#         video_writer.write(frame)
#
#     video_writer.release()
#
# import cv2
# import os

def create_video_from_images(image_folder, output_video_path, fps=25, resize=None, codec='mp4v', quality=95):
    images = sorted([img for img in os.listdir(image_folder) if img.endswith(".tiff")])
    frame = cv2.imread(os.path.join(image_folder, images[0]))
    if resize is not None:
        frame = cv2.resize(frame, resize)
    height, width, _ = frame.shape
    video_writer = cv2.VideoWriter(output_video_path, cv2.VideoWriter_fourcc(*codec), fps, (width, height))
    num_imgs = len(images)
    i = 0
    for image in images:
        img_path = os.path.join(image_folder, image)
        print(f"[{i}/{num_imgs}] processing {img_path}")
        frame = cv2.imread(img_path)
        if resize is not None:
            frame = cv2.resize(frame, resize)
        video_writer.write(frame)
        i += 1

    video_writer.release()

def make_video(image_folder):
    fldrs = image_folder.split("/")
    scan_nm = fldrs[-2] + "_" + fldrs[-1]
    base_dir = "/".join(d for d in fldrs[:-1])
    output_video_path = f"{base_dir}/{scan_nm}_video.mp4"
    #create_video_from_images(image_folder, output_video_path)

    resize = (480, 480)  # Specify the dimensions for resizing (width, height), set to None to keep original size
    codec = 'mp4v'  # Codec for video compression
    quality = 100  # Video quality, applicable if codec is set to 'mp4v' or 'DIVX'
    fps = 25  # Frames per second
    create_video_from_images(image_folder, output_video_path, fps, resize, codec, quality)


if __name__ == "__main__":

    image_folder = "T:/operations\STXM-data/ASTXM_upgrade_tmp/2024/guest/0408/A240408060/00_00"
    make_video(image_folder)
    print("video generation completed")