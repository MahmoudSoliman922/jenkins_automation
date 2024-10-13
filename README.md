# Ruby Aggregator

This project is a tool for running Ruby scripts through a Jenkins automation pipeline and aggregating the results. It consists of several components working together to execute Ruby scripts, interact with Jenkins, and process the output.

## Components

1. **ruby_script.rb**: An example Ruby script that performs data operations on ProjectsData units.

2. **ruby_aggregator.go**: A Go program that serves as the main entry point. It runs a Python script and processes Jenkins output.

3. **main.py**: A Python script that uses Playwright to interact with Jenkins, execute the Ruby script, and handle the output.

4. **go.mod**: The Go module file specifying the project's dependencies.

## Features

- Executes Ruby scripts through Jenkins automation
- Interacts with Jenkins API to manage builds
- Uses Playwright for web automation to interact with Jenkins UI
- Processes and parses Jenkins console output
- Optionally downloads result files from Jenkins

## Usage

To use this tool, run the Go program with the path to your Ruby script:

```
go run ruby_aggregator.go path/to/your/ruby_script.rb
```

The program will execute the Ruby script through Jenkins and process the output.

## Requirements

- Go 1.23.1 or later
- Python 3.x
- Playwright for Python
- Jenkins instance with appropriate job configurations

## Setup

1. Ensure Go and Python are installed on your system.
2. Install the required Python dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Install Playwright browsers:
   ```
   playwright install
   ```
4. Install the required Go dependencies (if any).
5. Configure Jenkins credentials and job details in the Python script.

## Note

This project is designed for a specific use case involving Jenkins automation and Ruby script execution. Ensure you have the necessary permissions and configurations in your Jenkins environment before using this tool.
