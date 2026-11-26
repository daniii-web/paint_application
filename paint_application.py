import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox
from PIL import Image, ImageDraw, ImageTk, ImageChops

# 1. BLUE COLOR PALETTE WITH PINK TEXT COLOR
BLUE_BG = "#B2D0F2"
BLUE_PANEL = "#84AFE1"
BLUE_BUTTON = "#1E2B65"
BLUE_HOVER = "#C3D7FC"
TEXT_COLOR = "#FE2495"
FONT_MAIN = ("Arial", 10, "bold")

# 2. MAIN WINDOW AND CANVAS SETTINGS
CANVAS_WIDTH = 900
CANVAS_HEIGHT = 550
MAX_UNDO = 30

root = tk.Tk()
root.title("My Paint Application")
root.geometry("1050x700")
root.configure(bg=BLUE_BG)

# Six one-click quick colors
QUICK_COLORS = ["black", "red", "blue", "green", "yellow", "indigo"]

# A frame around the canvas works as a blue border.
canvas_frame = tk.Frame(root, bg=BLUE_BUTTON, padx=4, pady=4)
canvas_frame.pack(padx=20, pady=(10, 5))

canvas = tk.Canvas(canvas_frame, width=CANVAS_WIDTH, height=CANVAS_HEIGHT,
                   bg="white", cursor="cross", highlightthickness=0)
canvas.pack()

# Pillow image stores the drawing so it can be saved.
image = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), "white")
draw = ImageDraw.Draw(image)
canvas_image = None

# 3. DRAWING SETTINGS
current_color = "black"
brush_size = 5
tool = "brush"
start_x = start_y = None
last_x = last_y = None
preview_shape = None

# History for Undo / Redo
undo_stack = []
redo_stack = []
pending_snapshot = None   # image copy taken when a stroke begins

# Filled-shape option
fill_var = tk.BooleanVar(value=False)

# Polygon shape (triangle) support
def triangle_points(x0, y0, x1, y1):
    return [((x0 + x1) / 2, y0), (x1, y1), (x0, y1)]

POLYGON_TOOL = {"triangle": triangle_points}
SHAPE_TOOLS = ("line", "rectangle", "oval") + tuple(POLYGON_TOOL)

tool_buttons = {}


# 4. TOOL FUNCTIONS
def set_color(color):
    """Change the drawing color (used by Choose Color and quick colors)."""
    global current_color, tool
    current_color = color
    if tool == "eraser":
        tool = "brush"
    color_button.config(bg=current_color)
    highlight_tool()

def choose_color():
    """Open the color chooser and update the drawing color."""
    selected = colorchooser.askcolor(title="Choose a color")
    if selected[1] is not None:
        set_color(selected[1])

def highlight_tool():
    """Show the active tool button in pink so the user can see it."""
    for name, button in tool_buttons.items():
        if name == tool:
            button.config(bg=TEXT_COLOR, fg="white", activeforeground="white")
        else:
            button.config(bg=BLUE_BUTTON, fg=TEXT_COLOR,
                          activeforeground=TEXT_COLOR)
    canvas.config(cursor="target" if tool == "eyedropper" else "cross")

def set_tool(selected_tool):
    """Change the active drawing tool."""
    global tool
    tool = selected_tool
    highlight_tool()

def change_brush_size(value):
    """Update the brush size using the slider."""
    global brush_size
    brush_size = int(float(value))

def normalize(x0, y0, x1, y1):
    """Return coordinates ordered so x0<=x1 and y0<=y1 (Pillow needs this)."""
    return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)


# 5. UNDO / REDO
def commit_snapshot():
    """Keep the pre-action snapshot only if the drawing actually changed."""
    global pending_snapshot
    if pending_snapshot is not None:
        if ImageChops.difference(pending_snapshot, image).getbbox() is not None:
            undo_stack.append(pending_snapshot)
            if len(undo_stack) > MAX_UNDO:
                undo_stack.pop(0)
            redo_stack.clear()
        pending_snapshot = None

def save_state_now():
    """Save the current image to the undo stack (for Clear / Open)."""
    undo_stack.append(image.copy())
    if len(undo_stack) > MAX_UNDO:
        undo_stack.pop(0)
    redo_stack.clear()

def undo(event=None):
    """Remove the most recent drawing action (stroke or shape)."""
    global image, draw
    if not undo_stack:
        return
    redo_stack.append(image.copy())
    image = undo_stack.pop()
    draw = ImageDraw.Draw(image)
    refresh_canvas()

def redo(event=None):
    """Bring back the action that was just undone."""
    global image, draw
    if not redo_stack:
        return
    undo_stack.append(image.copy())
    image = redo_stack.pop()
    draw = ImageDraw.Draw(image)
    refresh_canvas()


# 6. FREEHAND DRAWING
def pick_color(event):
    """Eyedropper: copy the color under the mouse, then go back to Brush."""
    global tool
    if 0 <= event.x < CANVAS_WIDTH and 0 <= event.y < CANVAS_HEIGHT:
        r, g, b = image.getpixel((event.x, event.y))[:3]
        tool = "brush"
        set_color(f"#{r:02x}{g:02x}{b:02x}")

def start_drawing(event):
    """Remember the mouse position when drawing starts."""
    global last_x, last_y, start_x, start_y, pending_snapshot
    if tool == "eyedropper":
        pick_color(event)
        start_x = start_y = None
        pending_snapshot = None
        return
    last_x, last_y = event.x, event.y
    start_x, start_y = event.x, event.y
    pending_snapshot = image.copy()      # for Undo

def draw_motion(event):
    """Draw while the left mouse button is held."""
    global last_x, last_y
    if tool == "eyedropper" or start_x is None:
        return
    color = "white" if tool == "eraser" else current_color
    if tool in ("brush", "eraser"):
        # Draw on the visible Tkinter canvas.
        canvas.create_line(last_x, last_y, event.x, event.y,
                           fill=color, width=brush_size,
                           capstyle=tk.ROUND, smooth=True)
        # Draw on the Pillow image for saving.
        draw.line((last_x, last_y, event.x, event.y),
                  fill=color, width=brush_size)
        last_x, last_y = event.x, event.y
    else:
        preview_shape_drawing(event)


# 7. SHAPE DRAWING
def preview_shape_drawing(event):
    """Show a temporary shape while the mouse is dragged."""
    global preview_shape
    if preview_shape is not None:
        canvas.delete(preview_shape)
    fill = current_color if fill_var.get() else ""
    if tool == "line":
        preview_shape = canvas.create_line(
            start_x, start_y, event.x, event.y,
            fill=current_color, width=brush_size)
    elif tool == "rectangle":
        preview_shape = canvas.create_rectangle(
            start_x, start_y, event.x, event.y,
            outline=current_color, fill=fill, width=brush_size)
    elif tool == "oval":
        preview_shape = canvas.create_oval(
            start_x, start_y, event.x, event.y,
            outline=current_color, fill=fill, width=brush_size)
    elif tool in POLYGON_TOOL:
        points = POLYGON_TOOL[tool](start_x, start_y, event.x, event.y)
        preview_shape = canvas.create_polygon(
            points, outline=current_color, fill=fill, width=brush_size)

def draw_polygon_on_image(points):
    """Draw a polygon (outline and optional fill) on the Pillow image."""
    if fill_var.get():
        draw.polygon(points, fill=current_color)
    # Closed outline drawn with lines so the brush size is respected.
    draw.line(points + [points[0]], fill=current_color,
              width=brush_size, joint="curve")

def finish_drawing(event):
    """Store the selected shape in the Pillow image."""
    global preview_shape
    if start_x is None:
        return
    fill = current_color if fill_var.get() else None
    x0, y0, x1, y1 = normalize(start_x, start_y, event.x, event.y)

    if tool == "line":
        draw.line((start_x, start_y, event.x, event.y),
                  fill=current_color, width=brush_size)
    elif tool == "rectangle":
        draw.rectangle((x0, y0, x1, y1), outline=current_color,
                       fill=fill, width=brush_size)
    elif tool == "oval":
        draw.ellipse((x0, y0, x1, y1), outline=current_color,
                     fill=fill, width=brush_size)
    elif tool in POLYGON_TOOL:
        draw_polygon_on_image(POLYGON_TOOL[tool](x0, y0, x1, y1))

    if tool in SHAPE_TOOLS:
        preview_shape = None
        refresh_canvas()
    commit_snapshot()


# 8. CANVAS MANAGEMENT
def refresh_canvas():
    """Display the current Pillow image on the Tkinter canvas."""
    global canvas_image
    canvas.delete("all")
    canvas_image = ImageTk.PhotoImage(image)
    canvas.create_image(0, 0, anchor="nw", image=canvas_image)

def clear_canvas():
    """Ask for confirmation, then replace the drawing with a blank image."""
    global image, draw, preview_shape
    answer = messagebox.askyesno("Clear canvas",
                                 "Are you sure you want to clear the drawing?")
    if not answer:
        return
    save_state_now()                     # so Undo can bring it back
    image = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), "white")
    draw = ImageDraw.Draw(image)
    preview_shape = None
    refresh_canvas()


# 9. OPEN AND SAVE IMAGE
def open_image():
    """Open an image and display it on the canvas."""
    global image, draw
    file_path = filedialog.askopenfilename(
        filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")])
    if file_path:
        try:
            opened_image = Image.open(file_path).convert("RGB")
            opened_image = opened_image.resize((CANVAS_WIDTH, CANVAS_HEIGHT))
            save_state_now()
            image = opened_image
            draw = ImageDraw.Draw(image)
            refresh_canvas()
        except Exception as error:
            messagebox.showerror("Error", f"Could not open image:\n{error}")

def save_image():
    """Save the current drawing as an image file."""
    file_path = filedialog.asksaveasfilename(
        defaultextension=".png",
        filetypes=[("PNG Image", "*.png"),
                   ("JPEG Image", "*.jpg"),
                   ("Bitmap Image", "*.bmp")])
    if file_path:
        try:
            image.save(file_path)
            messagebox.showinfo("Saved", "Your drawing has been saved!")
        except Exception as error:
            messagebox.showerror("Error", f"Could not save image:\n{error}")


# 10. TOOLBAR
def make_button(parent, text, command):
    """Create one blue button so we do not repeat the styling."""
    return tk.Button(parent, text=text, command=command,
                     bg=BLUE_BUTTON, fg=TEXT_COLOR,
                     activebackground=BLUE_HOVER, activeforeground=TEXT_COLOR,
                     font=FONT_MAIN, relief="flat", padx=10, pady=4,
                     cursor="hand2")

def make_tool_button(parent, text, tool_name):
    """Create a tool button that turns pink while it is active."""
    button = make_button(parent, text, lambda: set_tool(tool_name))
    button.pack(side="left", padx=4)
    tool_buttons[tool_name] = button

toolbar = tk.Frame(root, bg=BLUE_PANEL, padx=10, pady=4)
toolbar.pack(pady=3)

color_button = make_button(toolbar, "Choose Color", choose_color)
color_button.pack(side="left", padx=4)

make_tool_button(toolbar, "Brush", "brush")
make_tool_button(toolbar, "Eraser", "eraser")
make_tool_button(toolbar, "Line", "line")
make_tool_button(toolbar, "Rectangle", "rectangle")
make_tool_button(toolbar, "Oval", "oval")
make_tool_button(toolbar, "Triangle", "triangle")

tk.Label(toolbar, text="Brush Size:", bg=BLUE_PANEL,
         fg=TEXT_COLOR, font=FONT_MAIN).pack(side="left", padx=(10, 3))

size_slider = tk.Scale(toolbar, from_=1, to=100, orient="horizontal",
                       command=change_brush_size, length=100,
                       bg=BLUE_PANEL, fg=TEXT_COLOR,
                       troughcolor=BLUE_BUTTON, highlightthickness=0)
size_slider.set(5)
size_slider.pack(side="left", padx=3)

make_button(toolbar, "Clear", clear_canvas).pack(side="left", padx=4)
make_button(toolbar, "Open", open_image).pack(side="left", padx=4)
make_button(toolbar, "Save", save_image).pack(side="left", padx=4)

toolbar2 = tk.Frame(root, bg=BLUE_PANEL, padx=10, pady=4)
toolbar2.pack(pady=3)

make_button(toolbar2, "Undo", undo).pack(side="left", padx=4)
make_button(toolbar2, "Redo", redo).pack(side="left", padx=4)

tk.Checkbutton(toolbar2, text="Fill shapes", variable=fill_var,
               bg=BLUE_PANEL, fg=TEXT_COLOR,
               activebackground=BLUE_PANEL, activeforeground=TEXT_COLOR,
               selectcolor=BLUE_BUTTON, font=FONT_MAIN
               ).pack(side="left", padx=(6, 4))

make_tool_button(toolbar2, "Eyedropper", "eyedropper")

tk.Label(toolbar2, text="Colors:", bg=BLUE_PANEL,
         fg=TEXT_COLOR, font=FONT_MAIN).pack(side="left", padx=(10, 3))

for name in QUICK_COLORS:
    tk.Button(toolbar2, bg=name, width=3, relief="raised", cursor="hand2",
              activebackground=name,
              command=lambda c=name: set_color(c)).pack(side="left", padx=3)

# 11. CONNECT MOUSE EVENTS
canvas.bind("<Button-1>", start_drawing)
canvas.bind("<B1-Motion>", draw_motion)
canvas.bind("<ButtonRelease-1>", finish_drawing)

# Keyboard shortcuts
root.bind("<Control-z>", undo)
root.bind("<Control-y>", redo)

highlight_tool()

# 12. RUN THE APPLICATION
root.mainloop()