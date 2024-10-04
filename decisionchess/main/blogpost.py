# Run from main directory with python -m main.blogpost
import sys
import os
import markdown
import django

# Set the DJANGO_SETTINGS_MODULE environment variable
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "decisionchess.settings")

# Configure Django settings
django.setup()

# Given the above the model import should work and settings can be accessed
from main.models import BlogPosts
from django.utils import timezone


def create_blog_post(title, author, markdown_content):
    # Convert Markdown to HTML
    html_content = markdown.markdown(markdown_content, output_format='html5')
    print(html_content)

    # Create a new BlogPost instance
    new_post = BlogPosts(        
        title= title,
        author= author,
        content= html_content,
        timestamp= timezone.now()
        )
    
    # Save the new post to the database
    new_post.save()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python blogpost.py <file_path> <title> <author>")
        sys.exit(1)

    # Get the file path from the command-line argument
    file_path, title, author = sys.argv[1], sys.argv[2], sys.argv[3]

    try:
        # Open the file for reading
        with open(file_path, 'r') as file:
            # Read the file contents
            content = file.read()
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

    create_blog_post(title, author, content)
