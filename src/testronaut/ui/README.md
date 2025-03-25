# Testronaut UI Module

This module contains user interface components for the Testronaut application, built using the [Textual](https://textual.io/) framework for terminal applications.

## Database Browser

The database browser provides an interactive TUI (Text User Interface) for exploring CLI tools stored in the database. It allows you to:

- Browse all analyzed CLI tools
- View command hierarchies
- Examine detailed information about commands, options, and arguments
- Search for specific commands

### Running the Browser

You can run the database browser using the following command:

```bash
python -m testronaut analyze browser
```

To load a specific tool directly:

```bash
python -m testronaut analyze browser --tool <tool_name>
```

### Browser Controls

| Key       | Action                   |
|-----------|--------------------------|
| `↑` / `↓` | Navigate lists/tables    |
| `Enter`   | Select item              |
| `f`       | Focus search             |
| `r`       | Refresh data             |
| `Escape`  | Clear search             |
| `q`       | Quit                     |

### UI Components

1. **Tools Table** (Left Panel)
   - Displays all CLI tools in the database
   - Shows name, version, command count, and analysis date

2. **Command Tree** (Middle Panel)
   - Hierarchical view of commands
   - Supports nested subcommands

3. **Detail Panel** (Right Panel)
   - Displays detailed information about selected command
   - Shows options, arguments, examples, and help text

4. **Search** (Top of Left Panel)
   - Allows searching for commands by name or description

## Customization

The UI appearance is controlled by the CSS file at `styles/browser.tcss`. You can modify this file to customize the look and feel of the browser.

## Dependencies

- Textual: TUI framework for Python
- Rich: Terminal formatting library
- SQLModel: Database ORM

## Future Enhancements

- Filtering and sorting capabilities
- Search highlighting
- Export functionality
- Keyboard shortcuts for navigation
- Comparison between different versions of the same tool