/**
 * Code Editor functionality
 */

class CodeEditor {
    constructor(editorId) {
        this.editor = document.getElementById(editorId);
        this.setupEditor();
    }

    setupEditor() {
        // Add tab support
        this.editor.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                e.preventDefault();
                const start = this.editor.selectionStart;
                const end = this.editor.selectionEnd;
                const value = this.editor.value;

                // Insert 4 spaces
                this.editor.value = value.substring(0, start) + '    ' + value.substring(end);
                this.editor.selectionStart = this.editor.selectionEnd = start + 4;
            }
        });

        // Auto-indent on Enter
        this.editor.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const start = this.editor.selectionStart;
                const value = this.editor.value;
                
                // Find the start of the current line
                const lineStart = value.lastIndexOf('\n', start - 1) + 1;
                const currentLine = value.substring(lineStart, start);
                
                // Count leading spaces
                const indent = currentLine.match(/^\s*/)[0];
                
                // Check if line ends with colon (Python block start)
                const extraIndent = currentLine.trim().endsWith(':') ? '    ' : '';
                
                // Insert newline with indent
                const newText = '\n' + indent + extraIndent;
                this.editor.value = value.substring(0, start) + newText + value.substring(start);
                this.editor.selectionStart = this.editor.selectionEnd = start + newText.length;
            }
        });
    }

    getValue() {
        return this.editor.value;
    }

    setValue(code) {
        this.editor.value = code;
    }

    clear() {
        this.editor.value = '';
    }

    insertTemplate(template) {
        this.editor.value = template;
    }

    focus() {
        this.editor.focus();
    }
}

