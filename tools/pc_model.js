
export function createPCModel(THREE, scene) {
    const root = new THREE.Group();
    root.name = "Gaming PC";
    scene.add(root);

    const parts = new Map();
    const originalPositions = new Map();
    const movements = new Map();

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();

    let highlighted = null;

    const materials = {
        case: new THREE.MeshStandardMaterial({
            color: 0x20242b,
            metalness: 0.75,
            roughness: 0.35
        }),
        dark: new THREE.MeshStandardMaterial({
            color: 0x101318,
            metalness: 0.55,
            roughness: 0.4
        }),
        metal: new THREE.MeshStandardMaterial({
            color: 0x777e87,
            metalness: 0.85,
            roughness: 0.25
        }),
        silver: new THREE.MeshStandardMaterial({
            color: 0xb5bec8,
            metalness: 0.8,
            roughness: 0.3
        }),
        board: new THREE.MeshStandardMaterial({
            color: 0x183b31,
            metalness: 0.25,
            roughness: 0.65
        }),
        gold: new THREE.MeshStandardMaterial({
            color: 0xc99b42,
            metalness: 0.7,
            roughness: 0.3
        }),
        glass: new THREE.MeshPhysicalMaterial({
            color: 0x71869a,
            transparent: true,
            opacity: 0.16,
            roughness: 0.08,
            metalness: 0.15,
            transmission: 0.15,
            side: THREE.DoubleSide,
            depthWrite: false
        }),
        fanBlade: new THREE.MeshStandardMaterial({
            color: 0x303844,
            metalness: 0.45,
            roughness: 0.35,
            side: THREE.DoubleSide
        }),
        rgb: new THREE.MeshStandardMaterial({
            color: 0x64a9e8,
            emissive: 0x164d91,
            emissiveIntensity: 0.8,
            metalness: 0.3,
            roughness: 0.3
        })
    };

    function component(id, position = [0, 0, 0]) {
        const group = new THREE.Group();

        group.name = id;
        group.userData.componentId = id;
        group.position.set(...position);

        root.add(group);
        parts.set(id, group);

        return group;
    }

    function box(parent, size, position, material) {
        const mesh = new THREE.Mesh(
            new THREE.BoxGeometry(...size),
            material
        );

        mesh.position.set(...position);
        mesh.castShadow = true;
        mesh.receiveShadow = true;

        parent.add(mesh);
        return mesh;
    }

    function cylinder(parent, radius, depth, position, material) {
        const mesh = new THREE.Mesh(
            new THREE.CylinderGeometry(radius, radius, depth, 32),
            material
        );

        mesh.position.set(...position);
        mesh.rotation.x = Math.PI / 2;

        mesh.castShadow = true;
        parent.add(mesh);

        return mesh;
    }

    // Creates a detailed fan facing either X, Y or Z.
    function makeFan(id, position, radius, axis = "x") {
        const group = component(id, position);

        if (axis === "x") {
            group.rotation.y = Math.PI / 2;
        } else if (axis === "y") {
            group.rotation.x = -Math.PI / 2;
        }

        // Outer square frame
        box(
            group,
            [radius * 2.15, radius * 2.15, 0.12],
            [0, 0, 0],
            materials.dark
        );

        // Circular outer ring
        const ring = new THREE.Mesh(
            new THREE.TorusGeometry(radius * 0.86, 0.045, 8, 40),
            materials.metal
        );

        ring.position.z = 0.09;
        group.add(ring);

        // Seven individual fan blades
        const bladeShape = new THREE.Shape();

        bladeShape.moveTo(0.08 * radius, -0.05 * radius);
        bladeShape.quadraticCurveTo(
            0.42 * radius, -0.35 * radius,
            0.78 * radius, -0.12 * radius
        );
        bladeShape.quadraticCurveTo(
            0.88 * radius, 0.08 * radius,
            0.60 * radius, 0.22 * radius
        );
        bladeShape.quadraticCurveTo(
            0.30 * radius, 0.18 * radius,
            0.08 * radius, 0.05 * radius
        );
        bladeShape.closePath();

        const bladeGeometry = new THREE.ShapeGeometry(bladeShape);

        for (let i = 0; i < 7; i++) {
            const blade = new THREE.Mesh(
                bladeGeometry,
                materials.fanBlade
            );

            blade.rotation.z = i * (Math.PI * 2 / 7);
            blade.position.z = 0.11;

            group.add(blade);
        }

        // Central fan hub
        const hub = new THREE.Mesh(
            new THREE.CylinderGeometry(
                radius * 0.19,
                radius * 0.19,
                0.15,
                32
            ),
            materials.metal
        );

        hub.rotation.x = Math.PI / 2;
        hub.position.z = 0.14;

        group.add(hub);

        // Small gold centre
        const centre = new THREE.Mesh(
            new THREE.CircleGeometry(radius * 0.09, 24),
            materials.gold
        );

        centre.position.z = 0.23;
        group.add(centre);

        return group;
    }

    function addCable(id, points, radius = 0.045) {
        const group = component(id);

        const curve = new THREE.CatmullRomCurve3(
            points.map(p => new THREE.Vector3(...p))
        );

        const cable = new THREE.Mesh(
            new THREE.TubeGeometry(curve, 40, radius, 10, false),
            materials.dark
        );

        cable.castShadow = true;
        group.add(cable);

        return group;
    }

    // ------------------------------------------------
    // CASE
    // ------------------------------------------------

    const chassis = component("case");

    // Main rear wall
    box(
        chassis,
        [0.18, 6.8, 3.3],
        [-1.95, 3.5, 0],
        materials.case
    );

    // Bottom and top panels
    box(
        chassis,
        [4.0, 0.18, 3.5],
        [0, 0.15, 0],
        materials.case
    );

    box(
        chassis,
        [4.0, 0.16, 3.5],
        [0, 6.95, 0],
        materials.case
    );

    // Structural corner rails
    for (const x of [-1.9, 1.9]) {
        for (const z of [-1.65, 1.65]) {
            box(
                chassis,
                [0.14, 6.8, 0.14],
                [x, 3.5, z],
                materials.metal
            );
        }
    }

    // Front bezel frame
    for (const x of [-1.65, 1.65]) {
        box(
            chassis,
            [0.16, 6.4, 0.12],
            [x, 3.5, 1.76],
            materials.dark
        );
    }

    box(
        chassis,
        [3.3, 0.14, 0.12],
        [0, 6.7, 1.76],
        materials.dark
    );

    box(
        chassis,
        [3.3, 0.14, 0.12],
        [0, 0.35, 1.76],
        materials.dark
    );

    // Four case feet
    const feet = component("case_feet");

    for (const x of [-1.5, 1.5]) {
        for (const z of [-1.3, 1.3]) {
            box(
                feet,
                [0.65, 0.22, 0.55],
                [x, -0.04, z],
                materials.dark
            );
        }
    }

    // Removable tempered glass side panel
    const glass = component("glass_panel", [2.08, 3.5, 0]);

    box(
        glass,
        [0.035, 6.2, 2.9],
        [0, 0, 0],
        materials.glass
    );

    // Glass panel metal border
    for (const y of [-3.1, 3.1]) {
        box(
            glass,
            [0.07, 0.10, 3.0],
            [0, y, 0],
            materials.metal
        );
    }

    for (const z of [-1.48, 1.48]) {
        box(
            glass,
            [0.07, 6.2, 0.10],
            [0, 0, z],
            materials.metal
        );
    }

    // Glass mounting screws
    for (const y of [-2.8, 2.8]) {
        for (const z of [-1.35, 1.35]) {
            cylinder(
                glass,
                0.055,
                0.045,
                [0.06, y, z],
                materials.gold
            );
        }
    }

    // ------------------------------------------------
    // MOTHERBOARD
    // ------------------------------------------------

    const motherboard = component(
        "motherboard",
        [-1.65, 3.55, 0]
    );

    box(
        motherboard,
        [0.11, 5.65, 2.75],
        [0, 0, 0],
        materials.board
    );

    // Decorative PCB traces
    for (let i = 0; i < 12; i++) {
        box(
            motherboard,
            [0.025, 0.025, 0.5 + (i % 3) * 0.12],
            [0.065, -2.0 + i * 0.32, -0.75 + (i % 4) * 0.42],
            materials.gold
        );
    }

    // Motherboard mounting screws
    for (const y of [-2.45, 2.45, -0.8, 0.8]) {
        for (const z of [-1.1, 1.1]) {
            cylinder(
                motherboard,
                0.045,
                0.035,
                [0.08, y, z],
                materials.silver
            );
        }
    }

    // ------------------------------------------------
    // CPU AND COOLING
    // ------------------------------------------------

    const cpu = component("cpu", [-1.25, 4.55, 0.3]);

    box(
        cpu,
        [0.16, 0.57, 0.57],
        [0, 0, 0],
        materials.metal
    );

    box(
        cpu,
        [0.04, 0.43, 0.43],
        [0.10, 0, 0],
        materials.silver
    );

    // CPU cooler and heatsink fins
    const cooler = component(
        "cpu_cooler",
        [-0.82, 4.55, 0.3]
    );

    box(
        cooler,
        [0.48, 0.88, 0.95],
        [0, 0, 0],
        materials.metal
    );

    for (let i = 0; i < 11; i++) {
        box(
            cooler,
            [0.50, 0.035, 0.99],
            [0.02, -0.40 + i * 0.08, 0],
            materials.silver
        );
    }

    // CPU cooling fan
    makeFan("cpu_fan", [-0.52, 4.55, 0.3], 0.34, "x");

    // VRM heatsink
    const vrm = component(
        "vrm_heatsink",
        [-1.35, 5.45, 0.35]
    );

    box(
        vrm,
        [0.35, 0.48, 1.0],
        [0, 0, 0],
        materials.metal
    );

    for (let i = 0; i < 7; i++) {
        box(
            vrm,
            [0.38, 0.06, 0.04],
            [0.02, -0.19 + i * 0.06, 0],
            materials.silver
        );
    }

    // Chipset heatsink
    const chipset = component(
        "chipset_heatsink",
        [-1.30, 3.35, 1.05]
    );

    box(
        chipset,
        [0.26, 0.40, 0.48],
        [0, 0, 0],
        materials.metal
    );

    // ------------------------------------------------
    // RAM
    // ------------------------------------------------

    const ram = component("ram", [-1.02, 4.55, -0.65]);

    for (const z of [0, 0.30]) {
        // PCB
        box(
            ram,
            [0.13, 0.92, 0.17],
            [0, 0, z],
            materials.dark
        );

        // Aluminium heat spreader
        box(
            ram,
            [0.20, 0.78, 0.19],
            [0.02, 0, z],
            materials.metal
        );

        // Gold contacts
        for (let i = 0; i < 8; i++) {
            box(
                ram,
                [0.025, 0.10, 0.015],
                [0.09, -0.43, z - 0.07 + i * 0.02],
                materials.gold
            );
        }
    }

    // ------------------------------------------------
    // GPU
    // ------------------------------------------------

    const gpu = component(
        "gpu",
        [-0.15, 2.45, 0.15]
    );

    // GPU body
    box(
        gpu,
        [0.55, 0.65, 2.55],
        [0, 0, 0],
        materials.dark
    );

    // GPU aluminium backplate
    box(
        gpu,
        [0.09, 0.58, 2.38],
        [0.30, 0, 0],
        materials.metal
    );

    // Gold accent strip
    box(
        gpu,
        [0.025, 0.045, 2.25],
        [0.36, 0, 0],
        materials.gold
    );

    // Triple GPU fans
    makeFan(
        "gpu_fan_1",
        [0.145, 2.45, -0.67],
        0.28,
        "x"
    );

    makeFan(
        "gpu_fan_2",
        [0.145, 2.45, 0.15],
        0.28,
        "x"
    );

    makeFan(
        "gpu_fan_3",
        [0.145, 2.45, 0.97],
        0.28,
        "x"
    );

    // PCIe slots
    const pcie1 = component("pcie_slot_1", [-1.22, 2.6, 0.25]);
    box(
        pcie1,
        [0.18, 0.12, 1.8],
        [0, 0, 0],
        materials.dark
    );

    const pcie2 = component("pcie_slot_2", [-1.22, 1.95, 0.25]);
    box(
        pcie2,
        [0.18, 0.12, 1.5],
        [0, 0, 0],
        materials.dark
    );

    // ------------------------------------------------
    // STORAGE
    // ------------------------------------------------

    // M.2 NVMe SSD
    const nvme = component(
        "nvme_ssd",
        [-1.08, 3.75, -1.05]
    );

    box(
        nvme,
        [0.15, 0.13, 0.85],
        [0, 0, 0],
        materials.dark
    );

    box(
        nvme,
        [0.18, 0.08, 0.35],
        [0.08, 0, 0],
        materials.metal
    );

    // Traditional 2.5-inch SSD
    const ssd = component(
        "storage_ssd",
        [-0.45, 1.4, -0.9]
    );

    box(
        ssd,
        [0.65, 0.15, 0.95],
        [0, 0, 0],
        materials.metal
    );

    box(
        ssd,
        [0.66, 0.025, 0.96],
        [0, 0.09, 0],
        materials.dark
    );

    // ------------------------------------------------
    // POWER SUPPLY
    // ------------------------------------------------

    const psu = component(
        "psu",
        [-0.25, 0.75, -0.75]
    );

    box(
        psu,
        [1.0, 0.72, 1.35],
        [0, 0, 0],
        materials.dark
    );

    // PSU grille
    const psuGrille = component(
        "psu_fan_grille",
        [0.28, 0.75, -0.75]
    );

    const grille = new THREE.Mesh(
        new THREE.TorusGeometry(0.30, 0.025, 8, 40),
        materials.silver
    );

    psuGrille.rotation.y = Math.PI / 2;
    grille.rotation.y = Math.PI / 2;
    psuGrille.add(grille);

    // PSU fan
    makeFan(
        "psu_fan",
        [0.30, 0.75, -0.75],
        0.25,
        "x"
    );

    // ------------------------------------------------
    // CASE FANS
    // ------------------------------------------------

    makeFan(
        "front_fan",
        [-0.15, 5.55, 1.40],
        0.45,
        "z"
    );

    makeFan(
        "front_fan_2",
        [-0.15, 3.45, 1.40],
        0.45,
        "z"
    );

    makeFan(
        "front_fan_3",
        [-0.15, 1.35, 1.40],
        0.45,
        "z"
    );

    makeFan(
        "rear_fan",
        [-1.40, 5.65, -1.40],
        0.45,
        "z"
    );

    makeFan(
        "top_fan_1",
        [-0.25, 6.72, -0.65],
        0.38,
        "y"
    );

    makeFan(
        "top_fan_2",
        [-0.25, 6.72, 0.40],
        0.38,
        "y"
    );

    // ------------------------------------------------
    // POWER AND DATA CABLES
    // ------------------------------------------------

    addCable(
        "cable_24pin",
        [
            [-0.95, 4.3, 1.10],
            [-0.60, 4.0, 1.25],
            [-0.35, 3.5, 1.15],
            [-0.75, 3.1, 1.12]
        ],
        0.055
    );

    addCable(
        "cable_cpu",
        [
            [-0.95, 5.7, 0.95],
            [-0.70, 5.9, 0.8],
            [-0.45, 5.45, 0.6]
        ],
        0.045
    );

    addCable(
        "cable_gpu",
        [
            [-0.25, 2.9, 1.15],
            [0.20, 3.0, 1.30],
            [0.30, 2.7, 1.15]
        ],
        0.055
    );

    // ------------------------------------------------
    // FRONT AND REAR I/O
    // ------------------------------------------------

    const frontIO = component(
        "front_io",
        [1.25, 6.65, 1.78]
    );

    for (let i = 0; i < 3; i++) {
        box(
            frontIO,
            [0.18, 0.08, 0.035],
            [i * 0.25 - 0.25, 0, 0],
            materials.metal
        );
    }

    cylinder(
        frontIO,
        0.055,
        0.04,
        [0.55, 0, 0],
        materials.gold
    );

    const rearIO = component(
        "rear_io",
        [-1.92, 5.5, -0.9]
    );

    for (let i = 0; i < 6; i++) {
        box(
            rearIO,
            [0.08, 0.16, 0.22],
            [0, -0.8 + i * 0.30, 0],
            materials.dark
        );
    }

    // Power button on the front
    const powerButton = component(
        "power_button",
        [1.05, 6.65, 1.85]
    );

    cylinder(
        powerButton,
        0.12,
        0.10,
        [0, 0, 0],
        materials.gold
    );

    // ------------------------------------------------
    // SAVE ORIGINAL POSITIONS
    // ------------------------------------------------

    for (const [id, group] of parts) {
        originalPositions.set(id, group.position.clone());
    }

    // ------------------------------------------------
    // INTERACTION
    // ------------------------------------------------

    function pick(event, camera, renderer) {
        const rect = renderer.domElement.getBoundingClientRect();

        pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        raycaster.setFromCamera(pointer, camera);

        const hits = raycaster.intersectObject(root, true);

        if (hits.length === 0) return null;

        let object = hits[0].object;

        while (object && !object.userData.componentId) {
            object = object.parent;
        }

        return object?.userData.componentId ?? null;
    }

    function setHighlight(id) {
        if (highlighted) {
            scene.remove(highlighted);
            highlighted = null;
        }

        const group = parts.get(id);

        if (!group) return;

        highlighted = new THREE.BoxHelper(group, 0xffd447);
        highlighted.material.depthTest = false;
        highlighted.material.transparent = true;

        scene.add(highlighted);
    }

    function movePart(id, action) {
        const group = parts.get(id);
        const original = originalPositions.get(id);

        if (!group || !original) return;

        let target;

        if (action === "remove") {
            const slot = Array.from(movements.keys()).length;

            target = new THREE.Vector3(
                4.3,
                0.7 + (slot % 4) * 1.25,
                -1.0 + Math.floor(slot / 4) * 0.8
            );
        } else if (action === "install") {
            target = original.clone();
        } else {
            return;
        }

        movements.set(id, {
            from: group.position.clone(),
            to: target,
            elapsed: 0,
            duration: 0.45
        });
    }

    function update(delta) {
        for (const [id, movement] of movements) {
            const group = parts.get(id);

            movement.elapsed += delta;

            const t = Math.min(
                movement.elapsed / movement.duration,
                1
            );

            const eased = t * t * (3 - 2 * t);

            group.position.lerpVectors(
                movement.from,
                movement.to,
                eased
            );

            if (t >= 1) {
                movements.delete(id);
            }
        }

        if (highlighted) {
            highlighted.update();
        }
    }

    return {
        root,
        parts,
        pick,
        setHighlight,
        movePart,
        update
    };
}
