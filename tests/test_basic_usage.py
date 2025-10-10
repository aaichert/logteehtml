import sys
import traceback
from logteehtml.logteehtml import LogTeeHTML
from PIL import Image, ImageDraw

import io
import contextlib

import rich
from rich.progress import Progress
from rich.panel import Panel

import time

import tqdm

def run_progress_bar(with_delay, with_logger):
    print("Starting training for 3 epochs")
    print("Validation every 2 epochs")
    print("Checkpoint every 2 epochs")
    def run_inner(logger=None):
        with Progress(transient=True) as progress:
            task_train = progress.add_task("[red]Training...", total=3)
            task_val_period = progress.add_task("[green]Next Validation", total=2)
            for epoch in range(3):
                progress.advance(task_train)
                print(f"Epoch {epoch+1}/3: Dummy info")
                task_epoch = progress.add_task(f"[green]Epoch {epoch + 1}/3", total=10)
                for batch in range(5):
                    progress.advance(task_epoch)
                    print(f"  Batch {batch+1}/10: Dummy batch info")
                    if with_delay:
                        time.sleep(0.05)
                progress.remove_task(task_epoch)
                print(f"Epoch {epoch+1}, Loss: {0.1234 + epoch:.4f}")
                # Inject a fake table after each epoch if logger is present
                if logger is not None:
                    table_data = [
                        {"Metric": "Accuracy", "Value": f"{0.8 + 0.01*epoch:.2f}"},
                        {"Metric": "Loss", "Value": f"{0.1234 + epoch:.4f}"},
                        {"Metric": "LR", "Value": "1.23e-4"},
                    ]
                    logger.inject_table(table_data, anchor_text=f"Epoch {epoch+1} Results", text_preview=True)
                if (epoch + 1) % 2 == 0:
                    print(f"Validation Loss: {0.2345 + epoch:.4f}, LR: 1.23e-4")
                    print(f"Checkpoint saved: checkpoint_epoch_{epoch+1}.pt")

    if with_logger:
        with LogTeeHTML("test_log_progress", logfile_prefix="./", suffix="") as logger:
            run_inner(logger)
    else:
        run_inner()


def test_progress_bar_output_equality():
    """Test that progress bar output is the same with and without LogTeeHTML logger."""

    output = io.StringIO()
    print("### test_progress_bars without logger")
    with contextlib.redirect_stdout(output):
        run_progress_bar(False, False)
        output_no_logger = output.getvalue()

    print("### test_progress_bars with logger")
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        run_progress_bar(False, True)
        output_with_logger = output.getvalue()
    if output_no_logger != output_with_logger:
        print("--- Output without logger ---")
        print(output_no_logger)
        print("--- Output with logger ---")
        print(output_with_logger)
        raise AssertionError("Terminal output differs with and without logger!")
    else:
        print(output_with_logger)
        print("Terminal output is identical with and without logger.")

    print("Here is the output without stdout redirection:")
    run_progress_bar(True, True)

def test_ansi():
    print("Testing text styles:")
    print("\033[1mBold text\033[0m")
    print("\033[3mItalic text\033[0m")
    print("\033[4mUnderlined text\033[0m")
    print("\033[9mStrikethrough text\033[0m")
    print("\033[2mDim text\033[0m")
    print("\033[7mReverse text\033[0m")
    print("\nTesting colors:")
    for i in range(30, 38):
        print(f"\033[{i}mColor {i}\033[0m", end=" ")
    print()
    print("Bright colors:")
    for i in range(90, 98):
        print(f"\033[{i}mBright {i}\033[0m", end=" ")
    print()
    print("\nTesting background colors:")
    for i in range(40, 48):
        print(f"\033[{i}mBG {i}\033[0m", end=" ")
    print()
    print("Bright background colors:")
    for i in range(100, 108):
        print(f"\033[{i}mBright BG {i}\033[0m", end=" ")
    print()
    print("Combined foreground and background:")
    print(f"\033[31;42mRed on Green\033[0m \033[33;44mYellow on Blue\033[0m \033[97;41mWhite on Red\033[0m")
    print()
    print("Testing bright backgrounds (should auto-adjust foreground):")
    print(f"\033[107mAuto dark text on bright white\033[0m")
    print(f"\033[103mAuto dark text on bright yellow\033[0m") 
    print(f"\033[106mAuto dark text on bright cyan\033[0m")
    print()
    print("Testing color persistence across lines:")
    print("\033[32mThis should be green", end="")
    print(" - still green on same line")
    print("This should also be green on new line")
    print("And this line too\033[0m")
    print("This should be normal again")
    print()
    print("Testing incremental color changes:")
    print("\033[31mStarting with red text", end="")
    print("\033[44m now red text on blue background", end="")
    print("\033[93m now bright yellow text on blue background", end="")
    print("\033[102m now bright yellow on bright green background")
    print("Still bright yellow on bright green\033[0m")
    print("Back to normal")
    print()
    print("Testing background with no explicit foreground:")
    print(f"\033[41mJust red background\033[0m")
    print(f"\033[46mJust cyan background\033[0m") 
    print(f"\033[103mJust bright yellow background\033[0m")
    print(f"\033[107mJust bright white background\033[0m")
    print("\nTesting simple control sequences:")
    print("Before carriage return\rAfter CR")
    print("Line with clear", end="")
    print("\033[K")
    print("Should appear normally")
    print("\nTesting complex control sequences:")
    print("This has cursor movement\033[2AUp two lines")
    print("\nTesting mixed content:")
    print("\033[1;31mBold red text\033[0m with normal text")
    print('\nAnd test a Fake Progress report with 0, 50 and 100%')
    print("Fake Progress: \rFake Progress: 50%\rFake Progress: 100%")        


def run_fake_training_log(template):
    # Original log test code
    with LogTeeHTML(f"test_log_{template}", logfile_prefix="./", suffix="", template=template+'.html') as logger:
        print("Testing Rich Panel (should appear in terminal and HTML) ")
        panel = Panel("[green]Training Pipeline Started[/]", title="Status", border_style="green")
        rich.print(panel)
        rich.print("[red]Red Text[/]")
        
        logger.start("Enhanced ANSI Test")
        test_ansi()

        logger.start("Cursor Movement Grouping Test")
        for i in range(3):
            sys.stdout.write(f"Training... {i*10}%\r")
            sys.stdout.write("\x1b[K")  # Erase line
            sys.stdout.write(f"Epoch {i+1}/3       \r")
            sys.stdout.write("\x1b[A")  # Cursor up
        print("Done.")

        logger.start("Complex Progress Bars")
        print("Testing tqdm progress bar (should be grouped in details tag, not duplicated) ")
        for i in tqdm.tqdm(range(10), desc="tqdm test"):
            pass
        print("Testing table injection WITHOUT terminal preview ")
        table_data_no_preview = [
            {'test_type': 'HTML only', 'status': 'working', 'terminal_shown': False},
            {'test_type': 'Backend only', 'status': 'success', 'terminal_shown': False},
        ]
        print("This is before Table 1 (no preview)")
        logger.inject_table(table_data_no_preview, "Table Without Terminal Preview", text_preview=False)
        print("This is after Table 1")
        print("Testing table injection WITH terminal preview (Rich table) ")
        table_data_with_preview = [
            {'test_type': 'Rich table', 'status': 'working', 'terminal_shown': True},
            {'test_type': 'Dual output', 'status': 'success', 'terminal_shown': True},
        ]
        print("This is before Table 2 (with preview)")
        logger.inject_table(table_data_with_preview, "Table With Terminal Preview", text_preview=True)
        print("This is after Table 2")
        print("Testing image injection ")
        img = Image.new('RGB', (200, 100), color='blue')
        draw = ImageDraw.Draw(img)
        draw.text((10, 40), "Test Image", fill='white')
        logger.inject_image(img, anchor_text="Test Image", anchor_name="test-image")
        print("This is after image injection.")
        logger.start("stderr: how exceptions are printed")
        print("Testing stderr output ")
        try:
            print("About to crash...")
            raise RuntimeError("Simulated crash for stderr logging!")
        except Exception as e:
            print("Caught exception, printing to stderr:", file=sys.stderr)
            traceback.print_exc()
        print("Test Done")
    print("This should not be in the log.")

if __name__ == "__main__":
    for template in ['simple', 'pretty']:
        run_fake_training_log(template)
    test_progress_bar_output_equality()
