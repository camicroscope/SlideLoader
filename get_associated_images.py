import openslide
import os

dir = "./PDACG/images/"
out_dir = "./PDACG/images/associated/"

for fn in os.listdir(dir):
    if fn.endswith(".svs"):
        try:
            img = openslide.OpenSlide(dir + fn)
        except:
            print("[ERR]", fn)
            continue
        img_rgba  = img.associated_images;
        if "macro" in img_rgba:
            macro_rgb = img_rgba["macro"].convert("RGB");
        if "label" in img_rgba:
            label_rgb = img_rgba["label"].convert("RGB");
        if "thumbnail" in img_rgba:
            thumb_rgb = img_rgba["thumbnail"].convert("RGB");
        else:
            thumb_rgb = img.get_thumbnail((img_w,img_h)).convert("RGB");
        fname_pre = out_dir + "/" + os.path.splitext(fn)[0];
        if macro_rgb is not None:
            fname_out = fname_pre + "-macro.jpg";
            macro_rgb.save(fname_out);
        if label_rgb is not None:
            fname_out = fname_pre + "-label.jpg";
            label_rgb.save(fname_out);
        if thumb_rgb is not None:
            fname_out = fname_pre + "-thumb.jpg";
            thumb_rgb.save(fname_out);
        print("[OK]", fn)
