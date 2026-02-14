from PIL import Image, ImageDraw, ImageFont
import piexif
import os

def create_test_image():
    # Create a simple image
    img = Image.new('RGB', (800, 600), color = (73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((10,10), "URGENT: SHARE THIS NOW!", fill=(255, 255, 0))
    d.text((10,60), "The government is hiding the truth about 5G.", fill=(255, 255, 255))
    
    # Save it first
    img.save('test_fake.jpg')
    
    # Add suspicious EXIF
    zeroth_ifd = {
        piexif.ImageIFD.Make: "Canon",
        piexif.ImageIFD.Model: "Canon EOS 5D Mark IV",
        piexif.ImageIFD.Software: "Adobe Photoshop CC 2019 (Windows)"
    }
    exif_dict = {"0th": zeroth_ifd}
    exif_bytes = piexif.dump(exif_dict)
    
    img.save('test_fake.jpg', exif=exif_bytes)
    print("Created test_fake.jpg with suspicious EXIF and text.")

if __name__ == "__main__":
    create_test_image()
