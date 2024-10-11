package main

import (
	"bufio"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"strings"
	"time"
)

func runPythonScript(rubyScriptPath string) string {
	cmd := exec.Command("python3", "main.py", rubyScriptPath)

	// Create separate pipes for ordinary logs and Jenkins output
	ordinaryReader, ordinaryWriter := io.Pipe()
	jenkinsReader, jenkinsWriter := io.Pipe()

	cmd.Stdout = ordinaryWriter
	cmd.Stderr = jenkinsWriter

	// Create separate channels for ordinary logs and Jenkins output
	ordinaryLogChan := make(chan string)
	jenkinsLogChan := make(chan string)

	// Start goroutines to read from the pipes
	go readLogs(ordinaryReader, ordinaryLogChan)
	go readLogs(jenkinsReader, jenkinsLogChan)

	// Start the command
	if err := cmd.Start(); err != nil {
		log.Fatalf("Error starting command: %v", err)
	}

	var jenkinsOutput strings.Builder
	timeout := time.After(10 * time.Minute) // Set a timeout of 10 minutes
	jenkinsStarted := false
	jenkinsEnded := false

	for {
		select {
		case ordinaryLog, ok := <-ordinaryLogChan:
			if !ok {
				ordinaryLogChan = nil
				continue
			}
			fmt.Println("Ordinary log:", ordinaryLog)
		case jenkinsLog, ok := <-jenkinsLogChan:
			if !ok {
				jenkinsLogChan = nil
				continue
			}
			if strings.Contains(jenkinsLog, "START OF TASK [debug]") || strings.Contains(jenkinsLog, "START OF TASK [failure]") {
				jenkinsStarted = true
			}
			if jenkinsStarted {
				jenkinsOutput.WriteString(jenkinsLog + "\n")
				if strings.Contains(jenkinsLog, "END OF TASK [debug]") || strings.Contains(jenkinsLog, "END OF TASK [failure]") {
					jenkinsEnded = true
					return jenkinsOutput.String()
				}
			}
		case <-timeout:
			fmt.Println("Timeout: No Jenkins output received within 10 minutes.")
			cmd.Process.Kill()
			return jenkinsOutput.String()
		}

		if ordinaryLogChan == nil && jenkinsLogChan == nil {
			break
		}
	}

	if !jenkinsEnded {
		fmt.Println("Warning: Jenkins task did not complete normally.")
	}
	return jenkinsOutput.String()
}

func readLogs(reader io.Reader, logChan chan<- string) {
	scanner := bufio.NewScanner(reader)
	for scanner.Scan() {
		logChan <- scanner.Text()
	}
	close(logChan)
}

func parseJenkinsOutput(jenkinsOutput string) (map[string]interface{}, bool) {
	// Check if the output contains a failure message
	if strings.Contains(jenkinsOutput, "FAILED!") {
		// This is a failure case, return the entire output
		return map[string]interface{}{
			"status": "failed",
			"output": jenkinsOutput,
		}, true
	}

	// If not a failure, proceed with parsing as before
	lines := strings.Split(jenkinsOutput, "\n")
	var outputLines []string
	inOutputLines := false
	var errorMessage string
	var objectName string

	for _, line := range lines {
		trimmedLine := strings.TrimSpace(line)
		if strings.Contains(trimmedLine, "script_output.stdout_lines") {
			inOutputLines = true
			continue
		}
		if inOutputLines {
			if strings.HasPrefix(trimmedLine, "]") {
				break
			}
			// Remove leading/trailing whitespace, quotes, and comma
			cleanedLine := strings.Trim(trimmedLine, "\", ")
			if strings.HasPrefix(cleanedLine, "ERROR:") {
				errorMessage = cleanedLine
			} else if cleanedLine != "" && !strings.HasPrefix(cleanedLine, "|") {
				outputLines = append(outputLines, cleanedLine)
			}
		}
	}

	// Parse the Rails object
	railsObject := make(map[string]string)
	for _, line := range outputLines {
		if strings.HasPrefix(line, "[#<") {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) == 2 {
				objectName = strings.Trim(parts[0], "[#<")
			}
		} else if strings.Contains(line, ":") {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) == 2 {
				key := strings.TrimSpace(parts[0])
				value := strings.TrimSpace(parts[1])
				railsObject[key] = value
			}
		}
	}

	// Create the final structured output
	result := make(map[string]interface{})
	result["status"] = "success"
	result["error"] = errorMessage
	if objectName != "" {
		result[objectName] = railsObject
	}

	return result, true
}

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Please provide the path to the Ruby script as an argument.")
		os.Exit(1)
	}

	rubyScriptPath := os.Args[1]

	jenkinsOutput := runPythonScript(rubyScriptPath)

	fmt.Println(jenkinsOutput)

	// if jenkinsOutput == "" {
	// 	fmt.Println("No output from Jenkins automation script")
	// 	os.Exit(1)
	// }

	// // Parse the Jenkins output
	// parsedOutput, ok := parseJenkinsOutput(jenkinsOutput)
	// if !ok {
	// 	fmt.Println(jenkinsOutput)
	// 	return
	// }

	// for key, value := range parsedOutput {
	// 	fmt.Println("-", key, ":", value)
	// }
}
