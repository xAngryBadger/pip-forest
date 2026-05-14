STEP_TYPES = {
    "confirmar": {
        "description": "Yes/No confirmation toggle",
        "payload": {
            "type": "confirmar",
            "prompt": "str — Question text",
            "default": "bool — True=Sim, False=Nao",
        },
        "response": {"value": "bool or 'sim'/'nao'"},
        "mobile_component": "S/N Toggle (8.1)",
    },
    "pedir_float": {
        "description": "Decimal number input with validation",
        "payload": {
            "type": "pedir_float",
            "prompt": "str — Field label",
            "default": "float — Pre-filled value",
            "options": {"allow_zero": "bool"},
        },
        "response": {"value": "float"},
        "mobile_component": "Number Stepper (8.3)",
    },
    "pedir_int": {
        "description": "Integer number input with validation",
        "payload": {
            "type": "pedir_int",
            "prompt": "str — Field label",
            "default": "int — Pre-filled value",
            "options": {"allow_zero": "bool"},
        },
        "response": {"value": "int"},
        "mobile_component": "Number Stepper (8.3)",
    },
    "pedir_jornada": {
        "description": "Workday hours input (decimal or HH:MM format)",
        "payload": {
            "type": "pedir_jornada",
            "prompt": "str — Field label",
            "default": "float — Pre-filled value in hours",
        },
        "response": {"value": "float — hours (e.g. 6.5 or 6:30→6.5)"},
        "mobile_component": "Dual-Mode Decimal/Time Input (8.4)",
    },
    "selecionar": {
        "description": "Single selection from a list of options",
        "payload": {
            "type": "selecionar",
            "prompt": "str — Selection title",
            "default": "null",
            "options": {
                "items": "list[str] — Option labels",
                "zero_label": "str — Label for cancel/back (default 'Voltar')",
            },
        },
        "response": {"value": "str — Selected item text, or '0' for cancel"},
        "mobile_component": "Radio List (8.5)",
    },
    "selecionar_paginado": {
        "description": "Single selection from a paginated list",
        "payload": {
            "type": "selecionar_paginado",
            "prompt": "str — Selection title",
            "default": "null",
            "options": {
                "items": "list[str] — All option labels",
                "page_size": "int — Items per page (default 5)",
                "zero_label": "str — Label for cancel/back",
            },
        },
        "response": {"value": "str — Selected item number (1-indexed), '0' for cancel, '+'/'-' for page nav"},
        "mobile_component": "Paginated List (8.6)",
    },
    "prompt": {
        "description": "Free text input",
        "payload": {
            "type": "prompt",
            "prompt": "str — Field label",
            "default": "str or null — Pre-filled value",
        },
        "response": {"value": "str"},
        "mobile_component": "Text Field (8.2)",
    },
    "display": {
        "description": "Non-interactive information display (banner, list, summary)",
        "payload": {
            "type": "display",
            "prompt": "str — Title",
            "options": {
                "body": "str — Content (may contain newlines)",
                "level": "str — 'info' | 'warn' | 'error' | 'success'",
            },
        },
        "response": {"value": "'continuar' — User clicks Continuar button"},
        "mobile_component": "Banner (8.8) + Continuar button",
    },
    "table": {
        "description": "Tabular data display with headers and rows",
        "payload": {
            "type": "table",
            "prompt": "str — Table title",
            "options": {
                "headers": "list[str] — Column headers",
                "rows": "list[list[str]] — Row data",
            },
        },
        "response": {"value": "'continuar'"},
        "mobile_component": "Rich Table (8.10) + Continuar button",
    },
    "result": {
        "description": "Final result screen with downloadable files",
        "payload": {
            "type": "result",
            "prompt": "str — Result title (e.g. 'Concluido')",
            "options": {"files": "list[str] — Downloadable filenames"},
        },
        "response": {"value": "'menu' — Return to main menu"},
        "mobile_component": "Result Screen with download links",
    },
    "error": {
        "description": "Error screen — session terminated unexpectedly",
        "payload": {
            "type": "error",
            "prompt": "str — Error message",
            "options": {"error": "str — Full error detail"},
        },
        "response": {"value": "'menu' — Return to main menu"},
        "mobile_component": "Error Banner (8.8) + Return button",
    },
}
