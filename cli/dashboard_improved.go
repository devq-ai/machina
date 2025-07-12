package main

import (
	"fmt"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/spinner"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// Improved dashboard that shows all servers with wrapped descriptions
func runDashboardImproved() error {
	// Initialize spinner
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("#FF10F0"))

	// Create initial model
	model := dashboardModel{
		spinner:     s,
		loading:     true,
		selected:    0,
		gridWidth:   1,
		gridHeight:  13, // All 13 servers on one page
		dataLoadedAt: time.Time{},
	}

	// Create the Bubble Tea program
	p := tea.NewProgram(model, tea.WithAltScreen())
	_, err := p.Run()

	return err
}

// Improved server card rendering with full descriptions
func (m dashboardModel) renderImprovedServerCard(server MCPServer, selected bool) string {
	// Determine status color and symbol
	var statusStyle lipgloss.Style
	var symbol string
	if server.Status == "active" || server.Status == "production-ready" || server.Status == "running" {
		statusStyle = dashboardStatusRunning
		symbol = "●"
	} else {
		statusStyle = dashboardStatusStopped
		symbol = "●"
	}

	// Card style (selected or normal)
	var cardStyle lipgloss.Style
	if selected {
		cardStyle = dashboardSelectedStyle
	} else {
		cardStyle = dashboardItemStyle
	}

	// Wrap description at 75 characters
	description := server.Description
	if len(description) > 75 {
		words := strings.Fields(description)
		var lines []string
		var currentLine strings.Builder
		
		for _, word := range words {
			if currentLine.Len() + len(word) + 1 > 75 {
				if currentLine.Len() > 0 {
					lines = append(lines, currentLine.String())
					currentLine.Reset()
				}
			}
			if currentLine.Len() > 0 {
				currentLine.WriteString(" ")
			}
			currentLine.WriteString(word)
		}
		if currentLine.Len() > 0 {
			lines = append(lines, currentLine.String())
		}
		
		// Take first 2 lines
		if len(lines) > 2 {
			description = lines[0] + "\n    " + lines[1] + "..."
		} else if len(lines) > 1 {
			description = lines[0] + "\n    " + lines[1]
		} else {
			description = lines[0]
		}
	}

	// Create card content with full server name and wrapped description
	cardContent := fmt.Sprintf("%s %s\n  %s\n  %s • %d tools • %s",
		symbol, server.Name,
		description,
		server.Metadata.Category,
		len(server.Tools),
		server.Status)

	// Render wider card with more height for wrapped text
	card := cardStyle.
		Width(85).
		Height(5).
		Padding(0, 1).
		Border(lipgloss.RoundedBorder()).
		BorderForeground(statusStyle.GetForeground()).
		Render(cardContent)

	return card
}