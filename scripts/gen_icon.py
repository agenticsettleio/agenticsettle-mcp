"""Generate the agenticsettle-verify MCPB icon (rounded square + checkmark)."""
from PIL import Image, ImageDraw

SIZE = 512
BG = (15, 23, 42, 255)       # deep navy
ACCENT = (45, 212, 191, 255)  # teal — reads as "verified"
WHITE = (255, 255, 255, 255)

img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# rounded-square background
radius = 96
draw.rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=radius, fill=BG)

# teal ring
ring_margin = 64
draw.ellipse(
    [ring_margin, ring_margin, SIZE - ring_margin, SIZE - ring_margin],
    outline=ACCENT, width=22,
)

# checkmark
draw.line(
    [(158, 268), (226, 336), (354, 190)],
    fill=WHITE, width=40, joint="curve",
)
# round the checkmark endpoints/joint so it doesn't look clipped
for pt in [(158, 268), (226, 336), (354, 190)]:
    r = 20
    draw.ellipse([pt[0] - r, pt[1] - r, pt[0] + r, pt[1] + r], fill=WHITE)

img.save("assets/icon.png")
print("wrote assets/icon.png", img.size)
