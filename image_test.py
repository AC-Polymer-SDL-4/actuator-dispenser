from PIL import Image
import matplotlib.pyplot as plt

def average_rgb_in_center(image_path, square_size=100, show_crop=True):
    # Open and convert to RGB
    image = Image.open(image_path).convert('RGB')
    width, height = image.size

    # Define center and crop box
    half_size = square_size // 2
    center_x, center_y = width // 2, height // 2
    left = max(center_x - half_size, 0)
    top = max(center_y - half_size, 0)
    right = min(center_x + half_size, width)
    bottom = min(center_y + half_size, height)

    # Crop and get pixel data
    cropped = image.crop((left, top, right, bottom))
    pixels = list(cropped.getdata())
    num_pixels = len(pixels)

    # Compute average R, G, B
    avg_r = sum(p[0] for p in pixels) / num_pixels
    avg_g = sum(p[1] for p in pixels) / num_pixels
    avg_b = sum(p[2] for p in pixels) / num_pixels

    # Show the cropped image
    if show_crop:
        plt.imshow(cropped)
        plt.title(f'Center Crop ({square_size}x{square_size})')
        plt.axis('off')
        plt.show()

    return avg_r, avg_g, avg_b

# Example usage
if __name__ == '__main__':
    image_path = 'image.png'  # Your image path
    square_size = 100
    avg_r, avg_g, avg_b = average_rgb_in_center(image_path, square_size)
    print(f'Average RGB in center square ({square_size}x{square_size}):')
    print(f'R: {avg_r:.2f}, G: {avg_g:.2f}, B: {avg_b:.2f}')
