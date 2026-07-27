# Mind-map
Once, I was looking for the perfect mind map. But I couldn't find one that matched what I had in mind. So, I built my own. Hope you enjoy it!

## Unified Project Host

The Choogle/Mindmap portfolio is served by the Exam Flask application in
`../exam/app.py`. Run that single server and open `/` for the portfolio or
`/apps/exam/` for the Exam UI. `mindmap/server.py` remains a lightweight
standalone static preview server for the portfolio only.

# Branch

Branch is a browser-based mind mapping application built as a single HTML file. It focuses on simplicity, performance, and portability while providing advanced features commonly found in desktop mind mapping software.

The application runs entirely on the client side with no backend, no account requirements, and no installation. All data remains on the user's machine.

# Features

## Mind Mapping

- Infinite canvas
- Central root node
- Unlimited child and sibling nodes
- Automatic hierarchical branch coloring
- Inline node editing
- Node notes
- Branch collapse and expand
- Automatic node hierarchy visualization

## Navigation

- Smooth pan and zoom
- Recenter view
- Search and highlight nodes
- Keyboard shortcuts for rapid editing

## Organization

- Multi-selection
- Group multiple objects
- Custom grouping boundaries
- Shape annotations
- Freehand drawing
- Rectangle and ellipse tools

## Editing

- Undo / Redo
- Drag-and-drop nodes
- Automatic relationship rendering
- Branch restructuring

## Import / Export

- Save project as JSON
- Load existing JSON projects
- Export as PNG
- Export as PDF
- Export as standalone HTML
- Export as Markdown outline

# Architecture

The application is implemented as a single HTML document containing:

- HTML for the interface
- CSS for styling
- Vanilla JavaScript for application logic

No build tools, package managers, or frontend frameworks are required.

The entire application executes within the browser using the DOM, SVG, and Canvas-related browser APIs.

# How It Works

## Node System

Each node is stored as an object containing:

- Unique identifier
- Parent node reference
- Position
- Text content
- Notes
- Branch color
- Hierarchy depth
- Collapse state

Parent-child relationships form a tree structure that represents the complete mind map.

## Rendering Engine

Nodes are rendered as HTML elements.

Connections between nodes are rendered using SVG paths, allowing smooth curved links that automatically update whenever nodes move.

The rendering engine redraws only the necessary visual components whenever changes occur.

## Infinite Canvas

Instead of moving every node individually, the application transforms the entire workspace using:

- Translation
- Scaling

This enables smooth panning and zooming while maintaining rendering performance.

---

## Drawing Layer

Annotations are stored separately from mind map nodes.

Supported drawing objects include:

- Rectangle
- Ellipse
- Freehand paths

Each drawing object stores:

- Geometry
- Color
- Opacity
- Stroke style

This separation keeps annotations independent from the logical mind map.

---

## Group System

Groups do not duplicate nodes.

Instead, each group maintains references to its member objects, allowing grouped movement while preserving the original node structure.

---

## Search

The search engine performs client-side matching against node text.

Matching nodes are highlighted while unrelated nodes are visually dimmed.

---

## History System

Undo and redo functionality is implemented using application state snapshots.

Each editing operation stores a serialized copy of the application state, allowing complete restoration of previous versions.

---

## Export System

The application supports multiple export formats:

### JSON

Stores the complete editable project, including:

- Nodes
- Shapes
- Groups
- View settings

### PNG

Captures the visual workspace as an image.

### PDF

Generates a printable PDF version of the current mind map.

### HTML

Exports a standalone read-only HTML version that can be opened in any modern browser.

### Markdown

Converts the hierarchical node structure into an outline suitable for documentation.

---

# Technology Stack

- HTML5
- CSS3
- Vanilla JavaScript
- SVG
- jsPDF (PDF export)

---

# Browser Compatibility

Designed for modern browsers supporting:

- Chromium-based browsers
- Firefox
- Microsoft Edge
- Safari

---

# Running the Application

No installation is required.

Open the HTML file directly in a modern web browser.

The application executes entirely on the client side.

---

# Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Tab | Create child node |
| Enter | Create sibling node |
| Delete | Delete selected node |
| Double Click | Collapse or expand branch |
| Ctrl + Z | Undo |
| Ctrl + Shift + Z | Redo |
| Ctrl + G | Group selection |
| Shift + Click | Multi-select |
| Space + Drag | Pan canvas |
| Ctrl + Mouse Wheel | Zoom |

---

# Design Goals

- Single-file architecture
- No installation
- No backend
- No user accounts
- No cloud dependency
- Fully client-side execution
- Portable across operating systems
- Minimal external dependencies
- Responsive interaction for large mind maps

---

# License

Apache License 2.0
