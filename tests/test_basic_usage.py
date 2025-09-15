
import os
import sys
import traceback
from logteehtml.logteehtml import LogTeeHTML
import random
from PIL import Image, ImageDraw
import time

import rich
import rich.progress
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
import tqdm

def run_fake_training_log():

    with LogTeeHTML("Test Log", logfile_prefix="./") as logger:

        print("Testing Rich Panel (should appear in terminal and HTML) ")
        # Test simple Rich panel - create it once, print to terminal, then inject to HTML
        panel = Panel("[green]Training Pipeline Started[/]", title="Status", border_style="green")
        # Print to original stdout to avoid double capture
        rich.print(panel)
        rich.print("[red]Red Text[/]")


        logger.start("Enhanced ANSI Test")
        
        # Test text styles
        print("Testing text styles:")
        print("\033[1mBold text\033[0m")
        print("\033[3mItalic text\033[0m")
        print("\033[4mUnderlined text\033[0m")
        print("\033[9mStrikethrough text\033[0m")
        print("\033[2mDim text\033[0m")
        print("\033[7mReverse text\033[0m")
        
        # Test colors
        print("\nTesting colors:")
        for i in range(30, 38):
            print(f"\033[{i}mColor {i}\033[0m", end=" ")
        print()
        
        # Test bright colors
        print("Bright colors:")
        for i in range(90, 98):
            print(f"\033[{i}mBright {i}\033[0m", end=" ")
        print()
        
        # Test simple control sequences (should be handled smartly)
        print("\nTesting simple control sequences:")
        print("Before carriage return\rAfter CR")
        print("Line with clear", end="")
        print("\033[K")  # Clear to end of line
        print("Should appear normally")
        
        # Test complex control sequences (should use ANSI chunk)
        print("\nTesting complex control sequences:")
        print("This has cursor movement\033[2AUp two lines")
        
        # Test mixed content
        print("\nTesting mixed content:")
        print("\033[1;31mBold red text\033[0m with normal text")
        print('\nAnd test a Fake Progress report with 0, 50 and 100%')
        print("Fake Progress: \rFake Progress: 50%\rFake Progress: 100%")        

        logger.start("Complex Progress Bars")

        print("Testing tqdm progress bar (should be grouped in details tag, not duplicated) ")
        for i in tqdm.tqdm(range(10), desc="tqdm test"):
            time.sleep(0.1)

        print("Testing rich progress bar (terminal should be as expected but not visible in HTML) ")
        with Progress() as progress:
            task = progress.add_task("[cyan]Processing...", total=10)
            while not progress.finished:
                progress.update(task, advance=1)  # move bar forward
                time.sleep(0.1)  # simulate work

        print("Testing Rich Progress Bar (should be filtered out of HTML) ")
        # Test Rich Progress Bar
        with rich.progress.Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:
            
            task = progress.add_task("Processing epochs...", total=3)
            
            for epoch in range(3):
                logger.start(f"Epoch {epoch}")
                print(f"Epoch {epoch} running...")
                table_data = [
                    {'sample_id': f'A{epoch:02}', 'loss': round(random.uniform(0.08, 0.18), 3), 'error [mm]': round(random.uniform(0.7, 2.2), 2)},
                    {'sample_id': f'B{epoch:02}', 'loss': round(random.uniform(0.08, 0.18), 3), 'error [mm]': round(random.uniform(0.7, 2.2), 2)},
                ]
                print("Testing table injection (should appear in terminal AND HTML, but only once each) ")
                logger.inject_table(table_data, f"Validation Results Epoch {epoch}", text_preview=True)
                logger.anchor(f"End of Epoch {epoch}")
                
                progress.update(task, advance=1)

        logger.start("Injecting special content: Tables, Images, JSON")

        print("Testing table injection WITHOUT terminal preview ")
        table_data_no_preview = [
            {'test_type': 'HTML only', 'status': 'working', 'terminal_shown': False},
            {'test_type': 'Backend only', 'status': 'success', 'terminal_shown': False},
        ]
        logger.inject_table(table_data_no_preview, "Table Without Terminal Preview", text_preview=False)
        
        print("Testing table injection WITH terminal preview (Rich table) ")
        table_data_with_preview = [
            {'test_type': 'Rich table', 'status': 'working', 'terminal_shown': True},
            {'test_type': 'Dual output', 'status': 'success', 'terminal_shown': True},
        ]
        logger.inject_table(table_data_with_preview, "Table With Terminal Preview", text_preview=True)
        
        print("Testing image injection ")
        # Create a simple test image
        img = Image.new('RGB', (200, 100), color='blue')
        draw = ImageDraw.Draw(img)
        draw.text((10, 40), "Test Image", fill='white')
        logger.inject_image(img, anchor_text="Test Image", anchor_name="test-image")
        
        logger.start("stderr: how exceptions are printed")

        print("Testing stderr output ")
        # Simple stderr test - no Rich here
        try:
            print("About to crash...")
            raise RuntimeError("Simulated crash for stderr logging!")
        except Exception as e:
            print("Caught exception, printing to stderr:", file=sys.stderr)
            traceback.print_exc()
        print("Test Done")
    print("This should not be in the log.")

if __name__ == "__main__":
    run_fake_training_log()
