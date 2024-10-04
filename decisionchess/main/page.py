# Run from main directory with python -m main.page
import sys
import os
import markdown
import django

# Set the DJANGO_SETTINGS_MODULE environment variable
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "decisionchess.settings")

# Configure Django settings
django.setup()

# Given the above the model import should work and settings can be accessed
from main.models import Pages, Lessons, EmbeddedGames


def create_page(markdown_content, position, lesson, embedded_game):
    # Convert Markdown to HTML
    html_content = markdown.markdown(markdown_content, output_format='html5')
    print(html_content)

    # Create a new Page instance
    new_page = Pages(        
        lesson_id= lesson,
        content= html_content,
        embedded_game_id= embedded_game,
        page_position= position
        )
    
    # Save the new post to the database
    new_page.save()

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python page.py <file_path> <position> <lesson_title> <embedded_game_name>")
        print(len(sys.argv))
        sys.exit(1)

    # Get the file path from the command-line argument
    file_path, position, lesson_title, embedded_game_name = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

    try:
        position = int(position)
        # Open the file for reading
        with open(file_path, 'r') as file:
            # Read the file contents
            content = file.read()
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

    try:
        lesson = Lessons.objects.filter(title=lesson_title).first()
        if not lesson:
            print(f"No lesson found with title: {lesson_title}")
            sys.exit(1)

        embedded_game = EmbeddedGames.objects.filter(name=embedded_game_name).first()
        if not embedded_game:
            print(f"No embedded game found with name: {embedded_game_name}")
            sys.exit(1)

        create_page(content, position, lesson, embedded_game)

    except Lessons.DoesNotExist:
        print(f"No lesson found with title: {lesson_title}")
        sys.exit(1)
    except EmbeddedGames.DoesNotExist:
        print(f"No embedded game found with name: {embedded_game_name}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        sys.exit(1)