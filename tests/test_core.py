#!/usr/bin/env python3
"""
Simple test script for LogTeeHTML functionality.
Tests all major features: stages, print, HTML injection, image injection, and stream redirection.
"""

import os
import sys
import time as time_module
from PIL import Image, ImageDraw
import numpy as np

# Import the logger from package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from logteehtml import LogTeeHTML

def test_all_features():
    """Test all LogTeeHTML features in a single comprehensive log."""
    print("=== Starting Comprehensive LogTeeHTML Test ===")
    
    # Create a single logger with custom name and prefix
    logger = LogTeeHTML("comprehensive_test", prefix="demo", logfile_prefix="./")
    
    # === BASIC FUNCTIONALITY TEST ===
    logger.start("Basic Functionality")
    logger.print("Testing basic logging functionality...")
    
    # Test basic printing
    logger.print("This is a test message to stdout")
    logger.print("This is an error message", stderr=True)
    
    # Test multiple lines
    logger.print("Line 1\nLine 2\nLine 3")
    
    # Test with some ANSI escape sequences (basic colors)
    logger.print("\033[32mGreen text\033[0m and \033[31mRed text\033[0m")
    
    print("Basic functionality tests completed")
    
    # === STAGES AND CHAPTERS TEST ===
    logger.start("Data Loading")
    logger.print("Loading dataset from file...")
    logger.print("Dataset loaded successfully: 1000 samples")
    logger.print("Features: 784 dimensions")
    
    logger.start("Preprocessing")
    logger.print("Normalizing data...")
    logger.print("Applying transformations...")
    logger.print("Preprocessing complete")
    
    # === HTML INJECTION TEST ===
    logger.start("HTML Content Demo")
    
    # Test basic HTML injection
    logger.inject_html("<p><strong>Bold text</strong> and <em>italic text</em></p>", "Basic Styling")
    
    # Test table injection
    table_html = """
    <table border="1" style="border-collapse: collapse; margin: 10px 0;">
        <caption>Model Performance Comparison</caption>
        <tr style="background-color: #f2f2f2;"><th>Model</th><th>Accuracy</th><th>Loss</th></tr>
        <tr><td>ResNet-50</td><td>94.1%</td><td>0.23</td></tr>
        <tr><td>VGG-16</td><td>91.8%</td><td>0.31</td></tr>
        <tr><td>DenseNet</td><td>95.2%</td><td>0.19</td></tr>
    </table>
    """
    logger.inject_html(table_html, "Performance Table")
    
    # Test styled content
    styled_html = """
    <div style="background-color: #f0f8ff; padding: 15px; border-left: 4px solid #0066cc; margin: 10px 0;">
        <h3>Important Note</h3>
        <p>This is a highlighted information box with custom styling.</p>
        <ul>
            <li>Feature 1: Stream redirection</li>
            <li>Feature 2: HTML injection</li>
            <li>Feature 3: Image embedding</li>
        </ul>
    </div>
    """
    logger.inject_html(styled_html, "Feature Summary")
    
    # === IMAGE INJECTION TEST ===
    logger.start("Image Examples")
    
    # Create a simple test image using PIL
    img = Image.new('RGB', (200, 100), color='lightblue')
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "Test Image", fill='black')
    draw.rectangle([50, 30, 150, 80], outline='red', width=2)
    draw.ellipse([60, 40, 140, 70], outline='blue', width=2)
    
    logger.print("Injecting a simple test image with shapes...")
    logger.inject_image(img, "Test Shapes")
    
    # Create a gradient image
    width, height = 300, 150
    gradient = Image.new('RGB', (width, height))
    for x in range(width):
        for y in range(height):
            r = int(255 * x / width)
            g = int(255 * y / height)
            b = 128
            gradient.putpixel((x, y), (r, g, b))
    
    logger.print("Injecting a colorful gradient image...")
    logger.inject_image(gradient, "Color Gradient")
    
    # === RICH LIBRARY TEST ===
    logger.start("Rich Library Demo")
    
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.text import Text
        from rich.panel import Panel
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
        from rich.tree import Tree
        from rich.columns import Columns
        from rich.align import Align
        from rich import print as rich_print
        
        logger.print("Testing Rich library integration...")
        
        # Test rich print with colors and styles
        rich_print("[bold red]Bold red text[/bold red]")
        rich_print("[green]Green text[/green] and [blue]blue text[/blue]")
        rich_print("[italic yellow]Italic yellow text[/italic yellow]")
        
        # Create a comprehensive Rich table
        console = Console(record=True, width=100)
        table = Table(title="🚀 Model Performance Dashboard", show_header=True, header_style="bold magenta")
        table.add_column("Model", style="cyan", no_wrap=True)
        table.add_column("Accuracy", style="green", justify="right")
        table.add_column("Loss", style="red", justify="right")
        table.add_column("Status", style="bold", justify="center")
        table.add_column("Notes", style="dim")
        
        table.add_row("ResNet-50", "94.1%", "0.23", "✅ Pass", "Good convergence")
        table.add_row("VGG-16", "91.8%", "0.31", "⚠️ Review", "Slow training") 
        table.add_row("DenseNet", "95.2%", "0.19", "🎉 Best", "Outstanding performance")
        table.add_row("MobileNet", "89.5%", "0.42", "❌ Fail", "Needs optimization")
        
        console.print(table)
        rich_output = console.export_html(inline_styles=True)
        logger.inject_html(rich_output, "Performance Dashboard")
        
        # Create a progress bar simulation
        console = Console(record=True, width=80)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task1 = progress.add_task("[red]Downloading...", total=100)
            task2 = progress.add_task("[green]Processing...", total=100)
            task3 = progress.add_task("[cyan]Uploading...", total=100)
            
            # Simulate some progress
            for i in range(101):
                progress.update(task1, advance=1)
                if i > 30:
                    progress.update(task2, advance=1)
                if i > 60:
                    progress.update(task3, advance=1)
        
        progress_html = console.export_html(inline_styles=True)
        logger.inject_html(progress_html, "Progress Simulation")
        
        # Create a beautiful panel with nested content
        console = Console(record=True, width=90)
        
        # Create a tree structure
        tree = Tree("📁 Project Structure")
        tree.add("📄 README.md")
        data_branch = tree.add("📁 data/")
        data_branch.add("📊 train.csv")
        data_branch.add("📊 test.csv")
        models_branch = tree.add("📁 models/")
        models_branch.add("🧠 resnet50.pth")
        models_branch.add("🧠 vgg16.pth")
        
        # Create columns with different content
        column1 = Panel(tree, title="Files", border_style="blue", padding=(1, 2))
        
        metrics_text = Text()
        metrics_text.append("📈 Training Metrics\n\n", style="bold cyan")
        metrics_text.append("• Epoch: ", style="white")
        metrics_text.append("42/50\n", style="green")
        metrics_text.append("• Loss: ", style="white")
        metrics_text.append("0.1847\n", style="yellow")
        metrics_text.append("• Accuracy: ", style="white")
        metrics_text.append("94.3%\n", style="green bold")
        metrics_text.append("• Learning Rate: ", style="white")
        metrics_text.append("0.001", style="magenta")
        
        column2 = Panel(metrics_text, title="Metrics", border_style="green", padding=(1, 2))
        
        console.print(Columns([column1, column2], equal=True, expand=True))
        
        # Add a centered status panel
        status_panel = Panel(
            Align.center(
                Text("🎯 Training Complete!\nModel saved successfully.", 
                     style="bold green", justify="center")
            ),
            title="Status",
            border_style="green",
            padding=(1, 2)
        )
        console.print(status_panel)
        
        complex_html = console.export_html(inline_styles=True)
        logger.inject_html(complex_html, "Project Dashboard")
        
        # Create a syntax highlighted code block
        console = Console(record=True, width=100)
        from rich.syntax import Syntax
        
        code = '''
def train_model(model, dataloader, optimizer, criterion):
    """Advanced training function with rich logging."""
    model.train()
    total_loss = 0.0
    
    for batch_idx, (data, target) in enumerate(dataloader):
        optimizer.zero_grad()
        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
        
        if batch_idx % 100 == 0:
            print(f"Batch {batch_idx}, Loss: {loss.item():.4f}")
    
    return total_loss / len(dataloader)
        '''
        
        syntax = Syntax(code, "python", theme="monokai", line_numbers=True, word_wrap=True)
        console.print(Panel(syntax, title="🐍 Training Function", border_style="yellow"))
        
        code_html = console.export_html(inline_styles=True)
        logger.inject_html(code_html, "Code Example")
        
        logger.print("Rich library integration test completed with advanced features!")
        
    except ImportError:
        logger.print("Rich library not available - skipping Rich tests")
        logger.print("Install with: pip install rich")
    
    # === STREAM REDIRECTION TEST ===
    logger.start("Stream Redirection Demo")
    
    # These should be captured by the logger
    print("This print() call should be captured by the logger")
    print("Multiple", "arguments", "in", "print", sep=" ")
    
    # Test stderr
    import sys
    print("This goes to stderr and should be marked", file=sys.stderr)
    
    # Test with some built-in functions that use stdout
    print("Testing with range:", list(range(5)))
    
    # Simulate some progress-like output
    for i in range(3):
        print(f"Processing step {i+1}/3...", end="")
        time_module.sleep(0.1)
        print(" Done!")
    
    # === MODEL TRAINING SIMULATION ===
    logger.start("Model Training")
    logger.print("Initializing neural network...")
    logger.print("Training epoch 1/5...")
    print("Epoch 1 - Loss: 0.45, Accuracy: 87.2%")  # Should be captured
    
    logger.print("Training epoch 2/5...")
    print("Epoch 2 - Loss: 0.32, Accuracy: 91.1%")
    
    logger.print("Training epoch 3/5...")
    print("Epoch 3 - Loss: 0.25, Accuracy: 93.8%")
    
    # Create a simple training progress visualization
    progress_img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(progress_img)
    draw.text((10, 10), "Training Progress", fill='black')
    
    # Draw simple loss curve
    points = [(50, 150), (100, 120), (150, 100), (200, 90), (250, 85)]
    for i in range(len(points)-1):
        draw.line([points[i], points[i+1]], fill='red', width=2)
    draw.text((260, 80), "Loss", fill='red')
    
    # Draw accuracy curve
    acc_points = [(50, 180), (100, 160), (150, 140), (200, 120), (250, 110)]
    for i in range(len(acc_points)-1):
        draw.line([acc_points[i], acc_points[i+1]], fill='blue', width=2)
    draw.text((260, 105), "Accuracy", fill='blue')
    
    logger.inject_image(progress_img, "Training Progress Chart")
    
    # === FINAL RESULTS ===
    logger.start("Final Results")
    logger.print("Training completed successfully!")
    print("Final validation accuracy: 94.7%")  # Should be captured
    
    # Test mixed stdout/stderr
    print("Model performance metrics calculated", file=sys.stdout)
    print("Warning: Some edge cases may need attention", file=sys.stderr)
    
    logger.print("Model saved to: model_final.pth")
    
    # Final summary table
    summary_html = """
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin: 15px 0;">
        <h3 style="margin-top: 0;">🎉 Test Summary</h3>
        <p>All LogTeeHTML features have been successfully tested:</p>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px;">
            <div>✅ Basic logging</div>
            <div>✅ Stage management</div>
            <div>✅ HTML injection</div>
            <div>✅ Image embedding</div>
            <div>✅ Stream redirection</div>
            <div>✅ Error handling</div>
        </div>
    </div>
    """
    logger.inject_html(summary_html, "Test Summary")
    
    logger.print("Log files generated successfully!")
    logger.print("Test completed - check the generated HTML file for full results")
    
    print("All feature tests completed successfully!")
    return logger

def main():
    """Run the comprehensive test."""
    print("Starting LogTeeHTML single comprehensive test...")
    print("=" * 60)
    
    logger = None
    
    try:
        # Run the comprehensive test
        logger = test_all_features()
        
        print("\n" + "=" * 60)
        print("Test completed successfully!")
        print("\nGenerated files:")
        
        # List generated files
        for file in os.listdir("."):
            if file.endswith(('.txt', '.json', '.html')) and 'demo_comprehensive_test' in file:
                print(f"  - {file}")
        
        print(f"\nOpen 'demo_comprehensive_test_*.html' in a browser to view the formatted log!")
        print("Check the sidebar navigation to see all stages and HTML content.")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up logger to ensure files are written
        if logger:
            logger._cleanup()

if __name__ == "__main__":
    main()
