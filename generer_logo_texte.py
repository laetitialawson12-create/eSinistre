from PIL import Image, ImageDraw, ImageFont

font = ImageFont.truetype("gestion_sinistres/static/fonts/SCRIPTBL.TTF", 60)
color = (0, 45, 98)

img_tmp = Image.new("RGBA", (1, 1))
draw_tmp = ImageDraw.Draw(img_tmp)
lines = ["Fidélia", "assurances"]
widths = [draw_tmp.textbbox((0,0), l, font=font)[2] for l in lines]
width = max(widths) + 20
height = 140

img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
draw = ImageDraw.Draw(img)
draw.text((10, 0), "Fidélia", font=font, fill=color)
draw.text((10, 65), "assurances", font=font, fill=color)

img.save("gestion_sinistres/static/images/brand_scriptbold.png")
print("OK :", width, height)
