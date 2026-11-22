

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROCEDURES_DIR = ROOT / "assets" / "procedures"

PC_COMPONENTS = [
    ("case", "PC Case"),
    ("case_feet", "Case Feet"),
    ("motherboard", "Motherboard"),
    ("motherboard_capacitors", "Motherboard Capacitors"),
    ("cpu", "CPU"),
    ("cpu_cooler", "CPU Cooler"),
    ("cpu_fan", "CPU Cooling Fan"),
    ("ram", "RAM Modules"),
    ("vrm_heatsink", "VRM Heatsink"),
    ("chipset_heatsink", "Chipset Heatsink"),
    ("gpu", "Graphics Card"),
    ("gpu_fan_1", "GPU Fan 1"),
    ("gpu_fan_2", "GPU Fan 2"),
    ("gpu_fan_3", "GPU Fan 3"),
    ("pcie_slots", "PCIe Slots"),
    ("nvme_ssd", "M.2 NVMe SSD"),
    ("storage_ssd", "2.5-inch SSD"),
    ("psu", "Power Supply"),
    ("psu_fan", "Power Supply Fan"),
    ("psu_switch", "PSU On/Off Switch"),
    ("power_cable", "PSU Power Cable"),
    ("front_fan_1", "Front Fan 1"),
    ("front_fan_2", "Front Fan 2"),
    ("front_fan_3", "Front Fan 3"),
    ("rear_fan", "Rear Fan"),
    ("top_fan_1", "Top Fan 1"),
    ("top_fan_2", "Top Fan 2"),
    ("cable_24pin", "24-pin Motherboard Cable"),
    ("cable_cpu", "CPU Power Cable"),
    ("cable_gpu", "GPU Power Cable"),
    ("front_io", "Front I/O Ports"),
    ("rear_io", "Rear I/O Ports"),
    ("power_button", "Case Power Button"),
    ("glass_panel", "Tempered Glass Panel"),
]


components = [
    {
        "id": component_id,
        "label": label,
        "bounds": [0.01, 0.01, 0.99, 0.99]
    }
    for component_id, label in PC_COMPONENTS
]


steps = [
    {
        "id": "s01",
        "instruction": (
            "Shut down the PC through its operating system. "
            "Wait until all fans and lights have stopped. "
            "Click the power button to confirm the shutdown."
        ),
        "expected_action": "select",
        "component_id": "power_button",
        "explanation": (
            "Do not use Sleep. A full shutdown is required "
            "before working inside the computer."
        )
    },
    {
        "id": "s02",
        "instruction": (
            "Switch the power supply unit (PSU) to 0 (OFF)."
        ),
        "expected_action": "toggle",
        "component_id": "psu_switch",
        "explanation": (
            "The PSU switch disconnects the power supply's "
            "normal output from the system."
        )
    },
    {
        "id": "s03",
        "instruction": (
            "Disconnect the AC power cable from the back "
            "of the computer."
        ),
        "expected_action": "remove",
        "component_id": "power_cable",
        "explanation": (
            "The computer must be disconnected from mains "
            "power before internal components are handled."
        )
    },
    {
        "id": "s04",
        "instruction": (
            "Remove the tempered-glass side panel. "
            "Before handling RAM, use an anti-static wrist "
            "strap or touch unpainted, grounded metal on "
            "the case."
        ),
        "expected_action": "remove",
        "component_id": "glass_panel",
        "explanation": (
            "Electrostatic discharge can damage memory modules. "
            "Keep the power cable disconnected."
        )
    },
    {
        "id": "s05",
        "instruction": (
            "Remove the existing RAM modules from the "
            "motherboard."
        ),
        "expected_action": "remove",
        "component_id": "ram",
        "explanation": (
            "Release the memory slot's retaining clips, "
            "then lift the RAM modules straight out. "
            "Handle them by their edges."
        )
    },
    {
        "id": "s06",
        "instruction": (
            "Install the replacement RAM modules in the "
            "motherboard memory slots."
        ),
        "expected_action": "install",
        "component_id": "ram",
        "explanation": (
            "Align the notch in the RAM with the key in the "
            "slot. Press evenly until the retaining clips "
            "secure the module."
        )
    },
    {
        "id": "s07",
        "instruction": (
            "Reinstall the tempered-glass side panel."
        ),
        "expected_action": "install",
        "component_id": "glass_panel",
        "explanation": (
            "Make sure the panel is properly seated and secured."
        )
    },
    {
        "id": "s08",
        "instruction": (
            "Reconnect the AC power cable to the computer."
        ),
        "expected_action": "install",
        "component_id": "power_cable",
        "explanation": (
            "Reconnect power only after the internal work "
            "and case reassembly are complete."
        )
    },
    {
        "id": "s09",
        "instruction": (
            "Switch the PSU back to I (ON)."
        ),
        "expected_action": "toggle",
        "component_id": "psu_switch",
        "explanation": (
            "The PSU can be switched on after the power cable "
            "and case panel have been reconnected."
        )
    },
    {
        "id": "s10",
        "instruction": (
            "Press the case power button to start the PC."
        ),
        "expected_action": "select",
        "component_id": "power_button",
        "explanation": (
            "Check that the computer starts normally and "
            "that the replacement memory is detected."
        )
    }
]


procedure = {
    "schema_version": 1,
    "procedure_id": "ram_replacement_01",
    "content_version": "ram-01",
    "image": "pc_model_3d",
    "source": (
        "Stylised RAM replacement training simulation. "
        "Follow the specific computer and motherboard "
        "manufacturer's instructions in real maintenance."
    ),
    "components": components,
    "steps": steps,
    "hazard": {
        "trigger_after_step": "s03",
        "message": (
            "ELECTRICAL SAFETY ALERT: The mains cable is "
            "disconnected, but residual energy may remain "
            "in the system. Press and hold the case power "
            "button for approximately 5 seconds. This does "
            "NOT make the inside of the PSU safe to open. "
            "Never open the PSU."
        ),
        "correct_component_id": "power_button",
        "response_window_ms": 10000
    }
}


PROCEDURES_DIR.mkdir(parents=True, exist_ok=True)

output = PROCEDURES_DIR / "example_procedure.json"

output.write_text(
    json.dumps(procedure, indent=4),
    encoding="utf-8"
)

print(f"Created RAM replacement procedure: {output}")
print(f"Components: {len(components)}")
print(f"Steps: {len(steps)}")

