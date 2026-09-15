// Mock engineering data for Axiom IC Studio. No backend, all deterministic.

export type Status = "PASS" | "FAIL" | "WARN" | "NOT RUN";

export const PROJECT = {
  name: "aurora_65",
  technology: "Generic CMOS 65 nm",
  pdk: "gpdk65",
  supply: "1.2 V",
  topCell: "ota_core",
  description: "Two-stage fully differential operational transconductance amplifier",
};

export type TreeNode = {
  id: string;
  label: string;
  kind: "library" | "group" | "cell" | "view";
  view?: string;
  children?: TreeNode[];
};

export const DESIGN_TREE: TreeNode[] = [
  {
    id: "aurora_65",
    label: "aurora_65",
    kind: "library",
    children: [
      {
        id: "analog",
        label: "analog",
        kind: "group",
        children: [
          {
            id: "ota_core",
            label: "ota_core",
            kind: "cell",
            children: [
              { id: "ota_core:schematic", label: "schematic", kind: "view", view: "schematic" },
              { id: "ota_core:symbol", label: "symbol", kind: "view", view: "symbol" },
              { id: "ota_core:layout", label: "layout", kind: "view", view: "layout" },
              { id: "ota_core:extracted", label: "extracted", kind: "view", view: "extracted" },
            ],
          },
          {
            id: "bias_gen",
            label: "bias_gen",
            kind: "cell",
            children: [
              { id: "bias_gen:schematic", label: "schematic", kind: "view", view: "schematic" },
              { id: "bias_gen:symbol", label: "symbol", kind: "view", view: "symbol" },
              { id: "bias_gen:layout", label: "layout", kind: "view", view: "layout" },
            ],
          },
          {
            id: "cmfb",
            label: "cmfb",
            kind: "cell",
            children: [
              { id: "cmfb:schematic", label: "schematic", kind: "view", view: "schematic" },
              { id: "cmfb:symbol", label: "symbol", kind: "view", view: "symbol" },
            ],
          },
          {
            id: "current_mirror",
            label: "current_mirror",
            kind: "cell",
            children: [
              {
                id: "current_mirror:schematic",
                label: "schematic",
                kind: "view",
                view: "schematic",
              },
            ],
          },
          {
            id: "diff_pair",
            label: "diff_pair",
            kind: "cell",
            children: [
              { id: "diff_pair:schematic", label: "schematic", kind: "view", view: "schematic" },
            ],
          },
          {
            id: "output_stage",
            label: "output_stage",
            kind: "cell",
            children: [
              { id: "output_stage:schematic", label: "schematic", kind: "view", view: "schematic" },
              { id: "output_stage:extracted", label: "extracted", kind: "view", view: "extracted" },
            ],
          },
          {
            id: "startup",
            label: "startup",
            kind: "cell",
            children: [
              { id: "startup:schematic", label: "schematic", kind: "view", view: "schematic" },
            ],
          },
        ],
      },
      {
        id: "testbenches",
        label: "testbenches",
        kind: "group",
        children: [
          {
            id: "tb_ota_dc",
            label: "tb_ota_dc",
            kind: "cell",
            children: [
              { id: "tb_ota_dc:schematic", label: "schematic", kind: "view", view: "schematic" },
            ],
          },
          {
            id: "tb_ota_ac",
            label: "tb_ota_ac",
            kind: "cell",
            children: [
              { id: "tb_ota_ac:schematic", label: "schematic", kind: "view", view: "schematic" },
            ],
          },
          {
            id: "tb_ota_tran",
            label: "tb_ota_tran",
            kind: "cell",
            children: [
              { id: "tb_ota_tran:schematic", label: "schematic", kind: "view", view: "schematic" },
            ],
          },
          {
            id: "tb_ota_noise",
            label: "tb_ota_noise",
            kind: "cell",
            children: [
              { id: "tb_ota_noise:schematic", label: "schematic", kind: "view", view: "schematic" },
            ],
          },
          {
            id: "tb_ota_mc",
            label: "tb_ota_mc",
            kind: "cell",
            children: [
              { id: "tb_ota_mc:schematic", label: "schematic", kind: "view", view: "schematic" },
            ],
          },
        ],
      },
      { id: "digital", label: "digital", kind: "group", children: [] },
      { id: "models", label: "models", kind: "group", children: [] },
      { id: "verification", label: "verification", kind: "group", children: [] },
    ],
  },
];

export const LIBRARIES = [
  { name: "analogLib", cells: 214, path: "/pdk/analogLib", writable: false },
  { name: "basic", cells: 96, path: "/pdk/basic", writable: false },
  { name: "aurora_65", cells: 38, path: "/proj/aurora_65", writable: true },
  { name: "gpdk65", cells: 187, path: "/pdk/gpdk65", writable: false },
];

export const LIB_CELLS: Record<string, { name: string; views: string[]; modified: string }[]> = {
  aurora_65: [
    { name: "ota_core", views: ["schematic", "symbol", "layout", "extracted"], modified: "17:42" },
    { name: "bias_gen", views: ["schematic", "symbol", "layout"], modified: "16:19" },
    { name: "cmfb", views: ["schematic", "symbol"], modified: "14:51" },
    { name: "current_mirror", views: ["schematic", "symbol", "layout"], modified: "11:02" },
    { name: "diff_pair", views: ["schematic", "symbol", "layout"], modified: "10:44" },
    { name: "output_stage", views: ["schematic", "extracted"], modified: "09:38" },
    { name: "startup", views: ["schematic"], modified: "Yesterday" },
    { name: "tb_ota_ac", views: ["schematic"], modified: "17:41" },
  ],
  analogLib: [
    { name: "nmos", views: ["symbol"], modified: "—" },
    { name: "pmos", views: ["symbol"], modified: "—" },
    { name: "cap", views: ["symbol"], modified: "—" },
    { name: "res", views: ["symbol"], modified: "—" },
    { name: "idc", views: ["symbol"], modified: "—" },
    { name: "vdc", views: ["symbol"], modified: "—" },
  ],
  basic: [
    { name: "gnd", views: ["symbol"], modified: "—" },
    { name: "vdd", views: ["symbol"], modified: "—" },
    { name: "iopin", views: ["symbol"], modified: "—" },
  ],
  gpdk65: [
    { name: "nmos_1v2", views: ["symbol", "layout", "spectre"], modified: "—" },
    { name: "pmos_1v2", views: ["symbol", "layout", "spectre"], modified: "—" },
    { name: "nmos_lvt", views: ["symbol", "layout"], modified: "—" },
    { name: "mimcap", views: ["symbol", "layout"], modified: "—" },
    { name: "polyres", views: ["symbol", "layout"], modified: "—" },
  ],
};

// ---------------------------------------------------------------- schematic
export type Instance = {
  id: string;
  type: "nmos" | "pmos" | "cap" | "res" | "isrc" | "block";
  x: number;
  y: number;
  mirror?: boolean;
  cell: string;
  params: Record<string, string | number>;
  op?: Record<string, string>;
  conn?: Record<string, string>;
  warn?: string;
};

export const INSTANCES: Instance[] = [
  {
    id: "M1",
    type: "nmos",
    x: 300,
    y: 300,
    cell: "nmos_1v2",
    params: { W: "12u", L: "120n", nf: 4, m: 2 },
    conn: { D: "net17", G: "VINP", S: "tail", B: "VSS" },
    op: {
      VGS: "641.2 mV",
      VDS: "709.5 mV",
      IDS: "92.4 µA",
      gm: "1.31 mS",
      gds: "13.8 µS",
      region: "saturation",
    },
  },
  {
    id: "M2",
    type: "nmos",
    x: 460,
    y: 300,
    mirror: true,
    cell: "nmos_1v2",
    params: { W: "12u", L: "120n", nf: 4, m: 2 },
    conn: { D: "net18", G: "VINN", S: "tail", B: "VSS" },
    op: {
      VGS: "640.8 mV",
      VDS: "711.1 mV",
      IDS: "92.1 µA",
      gm: "1.30 mS",
      gds: "13.9 µS",
      region: "saturation",
    },
  },
  {
    id: "M3",
    type: "pmos",
    x: 300,
    y: 170,
    cell: "pmos_1v2",
    params: { W: "24u", L: "240n", nf: 8, m: 2 },
    conn: { D: "net17", G: "VCM", S: "VDD", B: "VDD" },
    op: {
      VGS: "-612.4 mV",
      VDS: "-489.0 mV",
      IDS: "92.4 µA",
      gm: "0.94 mS",
      gds: "9.1 µS",
      region: "saturation",
    },
  },
  {
    id: "M4",
    type: "pmos",
    x: 460,
    y: 170,
    mirror: true,
    cell: "pmos_1v2",
    params: { W: "24u", L: "240n", nf: 8, m: 2 },
    conn: { D: "net18", G: "VCM", S: "VDD", B: "VDD" },
    op: {
      VGS: "-611.9 mV",
      VDS: "-488.2 mV",
      IDS: "92.1 µA",
      gm: "0.93 mS",
      gds: "9.2 µS",
      region: "saturation",
    },
  },
  {
    id: "M5",
    type: "nmos",
    x: 380,
    y: 420,
    cell: "nmos_1v2",
    params: { W: "32u", L: "180n", nf: 8, m: 1 },
    conn: { D: "tail", G: "IBIAS", S: "VSS", B: "VSS" },
    op: {
      VGS: "588.4 mV",
      VDS: "312.6 mV",
      IDS: "184.5 µA",
      gm: "1.92 mS",
      gds: "8.4 µS",
      region: "saturation",
    },
  },
  {
    id: "M6",
    type: "pmos",
    x: 640,
    y: 170,
    cell: "pmos_1v2",
    params: { W: "48u", L: "180n", nf: 12, m: 2 },
    conn: { D: "VOUTP", G: "net17", S: "VDD", B: "VDD" },
    op: {
      VGS: "-488.8 mV",
      VDS: "-596.3 mV",
      IDS: "412.7 µA",
      gm: "3.81 mS",
      gds: "31.2 µS",
      region: "saturation",
    },
  },
  {
    id: "M7",
    type: "nmos",
    x: 640,
    y: 420,
    cell: "nmos_1v2",
    params: { W: "20u", L: "180n", nf: 6, m: 2 },
    conn: { D: "VOUTP", G: "IBIAS", S: "VSS", B: "VSS" },
    op: {
      VGS: "588.4 mV",
      VDS: "603.7 mV",
      IDS: "412.7 µA",
      gm: "3.44 mS",
      gds: "22.6 µS",
      region: "saturation",
    },
    warn: "Floating input: M7.G",
  },
  {
    id: "M8",
    type: "nmos",
    x: 780,
    y: 420,
    mirror: true,
    cell: "nmos_1v2",
    params: { W: "20u", L: "180n", nf: 6, m: 2 },
    conn: { D: "VOUTN", G: "IBIAS", S: "VSS", B: "VSS" },
    op: {
      VGS: "588.4 mV",
      VDS: "596.9 mV",
      IDS: "409.9 µA",
      gm: "3.42 mS",
      gds: "22.8 µS",
      region: "saturation",
    },
  },
  {
    id: "Ccomp",
    type: "cap",
    x: 566,
    y: 300,
    cell: "mimcap",
    params: { c: "1.4p" },
    conn: { P: "net17", N: "VOUTP" },
    op: { Q: "846.1 fC", V: "603.7 mV" },
  },
  {
    id: "Rz",
    type: "res",
    x: 566,
    y: 240,
    cell: "polyres",
    params: { r: "620" },
    conn: { A: "net17", B: "nz" },
    op: { I: "0.00 A", V: "0.00 V" },
  },
  {
    id: "IBIAS",
    type: "isrc",
    x: 180,
    y: 420,
    cell: "idc",
    params: { dc: "200u" },
    conn: { P: "VDD", N: "IBIAS" },
    op: { I: "200.0 µA" },
  },
  {
    id: "XBIAS",
    type: "block",
    x: 120,
    y: 200,
    cell: "bias_gen",
    params: { view: "schematic" },
    conn: { VDD: "VDD", VSS: "VSS", IOUT: "IBIAS" },
    op: { IOUT: "200.0 µA" },
  },
  {
    id: "XCMFB",
    type: "block",
    x: 830,
    y: 200,
    cell: "cmfb",
    params: { view: "schematic" },
    conn: { INP: "VOUTP", INN: "VOUTN", VCM: "VCM" },
    op: { VCM: "600.0 mV" },
  },
];

export type Net = {
  id: string;
  polyline: [number, number][][];
  voltage: string;
  connections: number;
  drivers: number;
  loads: number;
  cap: string;
  devices: string[];
};

export const NETS: Net[] = [
  {
    id: "VDD",
    polyline: [
      [
        [110, 100],
        [900, 100],
      ],
      [
        [330, 100],
        [330, 140],
      ],
      [
        [490, 100],
        [490, 140],
      ],
      [
        [670, 100],
        [670, 140],
      ],
      [
        [180, 100],
        [180, 400],
      ],
    ],
    voltage: "1.200 V",
    connections: 9,
    drivers: 1,
    loads: 8,
    cap: "412.7 fF",
    devices: ["M3", "M4", "M6", "IBIAS", "XBIAS", "XCMFB"],
  },
  {
    id: "VSS",
    polyline: [
      [
        [110, 520],
        [900, 520],
      ],
      [
        [410, 480],
        [410, 520],
      ],
      [
        [670, 480],
        [670, 520],
      ],
      [
        [810, 480],
        [810, 520],
      ],
    ],
    voltage: "0.000 V",
    connections: 11,
    drivers: 1,
    loads: 10,
    cap: "684.1 fF",
    devices: ["M1", "M2", "M5", "M7", "M8", "XBIAS"],
  },
  {
    id: "tail",
    polyline: [
      [
        [330, 360],
        [330, 390],
      ],
      [
        [330, 390],
        [490, 390],
      ],
      [
        [490, 390],
        [490, 360],
      ],
      [
        [410, 390],
        [410, 400],
      ],
    ],
    voltage: "312.6 mV",
    connections: 3,
    drivers: 1,
    loads: 2,
    cap: "44.8 fF",
    devices: ["M1", "M2", "M5"],
  },
  {
    id: "net17",
    polyline: [
      [
        [330, 200],
        [330, 260],
      ],
      [
        [330, 230],
        [560, 230],
      ],
      [
        [670, 230],
        [670, 140],
      ],
      [
        [596, 240],
        [670, 240],
      ],
      [
        [670, 230],
        [670, 246],
      ],
    ],
    voltage: "711.2 mV",
    connections: 4,
    drivers: 2,
    loads: 2,
    cap: "62.4 fF",
    devices: ["M1", "M3", "M6", "Ccomp"],
  },
  {
    id: "net18",
    polyline: [
      [
        [490, 200],
        [490, 260],
      ],
      [
        [490, 220],
        [810, 220],
      ],
      [
        [810, 220],
        [810, 400],
      ],
    ],
    voltage: "709.8 mV",
    connections: 4,
    drivers: 2,
    loads: 2,
    cap: "58.9 fF",
    devices: ["M2", "M4", "M8"],
  },
  {
    id: "VOUTP",
    polyline: [
      [
        [670, 200],
        [670, 400],
      ],
      [
        [670, 300],
        [740, 300],
      ],
      [
        [740, 300],
        [900, 300],
      ],
      [
        [596, 300],
        [670, 300],
      ],
    ],
    voltage: "603.7 mV",
    connections: 5,
    drivers: 2,
    loads: 3,
    cap: "86.2 fF",
    devices: ["M6", "M7", "Ccomp", "XCMFB"],
  },
  {
    id: "VOUTN",
    polyline: [
      [
        [810, 400],
        [810, 340],
      ],
      [
        [810, 340],
        [900, 340],
      ],
    ],
    voltage: "596.9 mV",
    connections: 4,
    drivers: 2,
    loads: 2,
    cap: "84.5 fF",
    devices: ["M8", "XCMFB"],
  },
  {
    id: "VINP",
    polyline: [
      [
        [200, 320],
        [286, 320],
      ],
    ],
    voltage: "600.0 mV",
    connections: 2,
    drivers: 1,
    loads: 1,
    cap: "18.2 fF",
    devices: ["M1"],
  },
  {
    id: "VINN",
    polyline: [
      [
        [504, 320],
        [560, 320],
      ],
    ],
    voltage: "600.0 mV",
    connections: 2,
    drivers: 1,
    loads: 1,
    cap: "18.4 fF",
    devices: ["M2"],
  },
  {
    id: "IBIAS",
    polyline: [
      [
        [180, 440],
        [180, 460],
      ],
      [
        [180, 460],
        [800, 460],
      ],
      [
        [410, 440],
        [410, 460],
      ],
      [
        [670, 440],
        [670, 460],
      ],
      [
        [800, 440],
        [800, 460],
      ],
    ],
    voltage: "588.4 mV",
    connections: 4,
    drivers: 1,
    loads: 3,
    cap: "36.9 fF",
    devices: ["M5", "M7", "M8", "IBIAS"],
  },
  {
    id: "VCM",
    polyline: [
      [
        [330, 160],
        [490, 160],
      ],
      [
        [490, 160],
        [860, 160],
      ],
      [
        [330, 160],
        [330, 148],
      ],
    ],
    voltage: "612.4 mV",
    connections: 3,
    drivers: 1,
    loads: 2,
    cap: "29.4 fF",
    devices: ["M3", "M4", "XCMFB"],
  },
];

export const SCHEM_PINS = [
  { name: "VINP", x: 200, y: 320, dir: "in" },
  { name: "VINN", x: 560, y: 320, dir: "in" },
  { name: "VOUTP", x: 900, y: 300, dir: "out" },
  { name: "VOUTN", x: 900, y: 340, dir: "out" },
  { name: "VCM", x: 860, y: 160, dir: "in" },
  { name: "IBIAS", x: 180, y: 460, dir: "in" },
];

// ---------------------------------------------------------------- layout
export const LAYERS = [
  { name: "NWELL", purpose: "drawing", color: "#8f7f2a", fill: 0.28 },
  { name: "DIFF", purpose: "drawing", color: "#3f9e4d", fill: 0.55 },
  { name: "POLY", purpose: "drawing", color: "#d0453f", fill: 0.7 },
  { name: "CONT", purpose: "drawing", color: "#c9ccd4", fill: 0.85 },
  { name: "M1", purpose: "drawing", color: "#4b93ff", fill: 0.55 },
  { name: "V1", purpose: "drawing", color: "#e8eaee", fill: 0.9 },
  { name: "M2", purpose: "drawing", color: "#b68cff", fill: 0.5 },
  { name: "V2", purpose: "drawing", color: "#d9c7ff", fill: 0.9 },
  { name: "M3", purpose: "drawing", color: "#58d6e8", fill: 0.45 },
  { name: "M4", purpose: "drawing", color: "#e89a4a", fill: 0.45 },
  { name: "PIN", purpose: "label", color: "#45c486", fill: 0.9 },
];

export type Shape = {
  layer: string;
  x: number;
  y: number;
  w: number;
  h: number;
  label?: string;
  device?: string;
  net?: string;
};

function buildLayout(): Shape[] {
  const s: Shape[] = [];
  // guard ring / well
  s.push({ layer: "NWELL", x: 20, y: 16, w: 700, h: 180 });
  for (const [x, y, w, h] of [
    [12, 8, 716, 8],
    [12, 8, 8, 420],
    [720, 8, 8, 420],
    [12, 420, 716, 8],
  ] as const) {
    s.push({ layer: "M1", x, y, w, h, net: "VSS" });
    s.push({ layer: "DIFF", x: x + 1, y: y + 1, w: w - 2, h: h - 2 });
  }
  // PMOS array (common centroid) top
  for (let i = 0; i < 16; i++) {
    const x = 60 + i * 40;
    s.push({ layer: "DIFF", x, y: 40, w: 30, h: 120, device: i % 2 ? "M4" : "M3" });
    s.push({ layer: "POLY", x: x + 11, y: 28, w: 8, h: 146, device: i % 2 ? "M4" : "M3" });
    s.push({ layer: "M1", x: x - 4, y: 44, w: 12, h: 110, net: i % 2 ? "net18" : "net17" });
    s.push({ layer: "CONT", x: x - 1, y: 60, w: 5, h: 5 });
    s.push({ layer: "CONT", x: x - 1, y: 130, w: 5, h: 5 });
  }
  // NMOS input pair array
  for (let i = 0; i < 12; i++) {
    const x = 90 + i * 46;
    s.push({ layer: "DIFF", x, y: 230, w: 34, h: 96, device: i % 2 ? "M2" : "M1" });
    s.push({ layer: "POLY", x: x + 13, y: 218, w: 8, h: 122, device: i % 2 ? "M2" : "M1" });
    s.push({ layer: "M1", x: x - 5, y: 236, w: 13, h: 84, net: "tail" });
    s.push({ layer: "CONT", x: x - 2, y: 250, w: 5, h: 5 });
    s.push({ layer: "CONT", x: x - 2, y: 300, w: 5, h: 5 });
  }
  // dummy devices
  s.push({ layer: "DIFF", x: 40, y: 230, w: 30, h: 96, device: "DUMMY" });
  s.push({ layer: "POLY", x: 51, y: 218, w: 8, h: 122, device: "DUMMY" });
  s.push({ layer: "DIFF", x: 664, y: 230, w: 30, h: 96, device: "DUMMY" });
  s.push({ layer: "POLY", x: 675, y: 218, w: 8, h: 122, device: "DUMMY" });
  // tail device
  s.push({ layer: "DIFF", x: 120, y: 356, w: 420, h: 44, device: "M5" });
  for (let i = 0; i < 8; i++)
    s.push({ layer: "POLY", x: 136 + i * 52, y: 346, w: 10, h: 64, device: "M5" });
  // output devices
  s.push({ layer: "DIFF", x: 560, y: 356, w: 130, h: 44, device: "M7" });
  for (let i = 0; i < 4; i++)
    s.push({ layer: "POLY", x: 574 + i * 32, y: 346, w: 10, h: 64, device: "M7" });
  // metal buses
  s.push({ layer: "M2", x: 30, y: 200, w: 680, h: 14, net: "VDD", label: "VDD" });
  s.push({ layer: "M2", x: 30, y: 340, w: 680, h: 12, net: "VSS", label: "VSS" });
  s.push({ layer: "M3", x: 40, y: 170, w: 640, h: 10, net: "VCM" });
  s.push({ layer: "M3", x: 380, y: 60, w: 12, h: 300, net: "VOUTP", label: "VOUTP" });
  s.push({ layer: "M4", x: 430, y: 60, w: 12, h: 300, net: "VOUTN", label: "VOUTN" });
  s.push({ layer: "M2", x: 60, y: 404, w: 600, h: 10, net: "IBIAS" });
  for (let i = 0; i < 14; i++) {
    s.push({ layer: "V1", x: 60 + i * 48, y: 203, w: 8, h: 8 });
    s.push({ layer: "V2", x: 60 + i * 48, y: 342, w: 8, h: 8 });
  }
  // pins
  s.push({ layer: "PIN", x: 24, y: 246, w: 16, h: 16, label: "VINP", net: "VINP" });
  s.push({ layer: "PIN", x: 700, y: 246, w: 16, h: 16, label: "VINN", net: "VINN" });
  s.push({ layer: "PIN", x: 374, y: 20, w: 20, h: 16, label: "VOUTP", net: "VOUTP" });
  s.push({ layer: "PIN", x: 424, y: 20, w: 20, h: 16, label: "VOUTN", net: "VOUTN" });
  s.push({ layer: "PIN", x: 24, y: 400, w: 16, h: 16, label: "IBIAS", net: "IBIAS" });
  return s;
}

export const LAYOUT_SHAPES = buildLayout();

export const RATLINES: { x1: number; y1: number; x2: number; y2: number; net: string }[] = [
  { x1: 120, y1: 250, x2: 380, y2: 100, net: "net17" },
  { x1: 300, y1: 380, x2: 620, y2: 380, net: "IBIAS" },
  { x1: 500, y1: 250, x2: 660, y2: 180, net: "VCM" },
];

// ---------------------------------------------------------------- simulation
export const DESIGN_VARIABLES = [
  { name: "VDD", value: "1.2", unit: "V" },
  { name: "IBIAS", value: "200", unit: "µA" },
  { name: "CLOAD", value: "1.0", unit: "pF" },
  { name: "TEMP", value: "27", unit: "°C" },
  { name: "VCM", value: "0.6", unit: "V" },
];

export const ANALYSES = [
  {
    id: "dcOp",
    enabled: true,
    rows: [
      ["Save DC", "yes"],
      ["Temperature", "27 °C"],
    ],
  },
  {
    id: "ac",
    enabled: true,
    rows: [
      ["Start", "1 Hz"],
      ["Stop", "10 GHz"],
      ["Points", "50/dec"],
    ],
  },
  {
    id: "tran",
    enabled: false,
    rows: [
      ["Stop", "10 µs"],
      ["Max step", "1 ns"],
    ],
  },
  { id: "noise", enabled: false, rows: [["Output", "VOUTP"]] },
  { id: "stb", enabled: false, rows: [["Probe", "iprb0"]] },
  { id: "pss", enabled: false, rows: [["Fund", "10 MHz"]] },
  { id: "pac", enabled: false, rows: [["Maxsideband", "5"]] },
];

export type OutputRow = {
  name: string;
  expr: string;
  result: string;
  spec: string;
  status: Status;
  nets?: string[];
};

export const OUTPUTS: OutputRow[] = [
  {
    name: "DC Gain",
    expr: "gain(VOUT/VID)",
    result: "67.41 dB",
    spec: "> 60 dB",
    status: "PASS",
    nets: ["VOUTP", "VOUTN"],
  },
  {
    name: "UGBW",
    expr: "unityGainFreq",
    result: "184.2 MHz",
    spec: "> 150 MHz",
    status: "PASS",
    nets: ["VOUTP"],
  },
  {
    name: "Phase Margin",
    expr: "phaseMargin",
    result: "63.8 °",
    spec: "> 60 °",
    status: "PASS",
    nets: ["VOUTP"],
  },
  {
    name: "Slew Rate +",
    expr: "slewRate",
    result: "42.1 V/µs",
    spec: "> 35 V/µs",
    status: "PASS",
    nets: ["VOUTP"],
  },
  {
    name: "Noise",
    expr: "integratedNoise",
    result: "18.63 µVrms",
    spec: "< 20 µVrms",
    status: "PASS",
    nets: ["VOUTP"],
  },
  {
    name: "Power",
    expr: "averagePower",
    result: "2.41 mW",
    spec: "< 2.5 mW",
    status: "PASS",
    nets: ["VDD"],
  },
  {
    name: "Output Swing",
    expr: "swing",
    result: "0.91 V",
    spec: "> 0.95 V",
    status: "FAIL",
    nets: ["VOUTP", "VOUTN"],
  },
];

export const CORNERS = [
  { id: "TT", temp: "27", supply: "1.20", enabled: true },
  { id: "FF", temp: "-40", supply: "1.32", enabled: true },
  { id: "SS", temp: "125", supply: "1.08", enabled: true },
  { id: "FS", temp: "27", supply: "1.20", enabled: true },
  { id: "SF", temp: "27", supply: "1.20", enabled: true },
];

export const TESTS = [
  "AC Performance",
  "Transient",
  "Noise",
  "Stability",
  "Power",
  "Startup",
] as const;

export type MatrixRow = {
  test: string;
  corner: string;
  temp: string;
  supply: string;
  status: Status;
  runtime: string;
  gain: string;
  ugbw: string;
  pm: string;
  noise: string;
  power: string;
};

function hash(s: string) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return Math.abs(h % 10000) / 10000;
}

export const MATRIX: MatrixRow[] = TESTS.flatMap((test) =>
  CORNERS.map((c) => {
    const r = hash(test + c.id);
    const bad = c.id === "SS" && (test === "AC Performance" || test === "Stability");
    const warn = c.id === "SS" && test === "Startup";
    const gain = 67.4 - (c.id === "SS" ? 6.2 : c.id === "FF" ? -1.4 : r * 1.4);
    const ugbw = 184.2 - (c.id === "SS" ? 44.7 : c.id === "FF" ? -12.1 : r * 7);
    const pm = 63.8 - (c.id === "SS" ? 8.5 : r * 2.2);
    return {
      test,
      corner: c.id,
      temp: c.temp,
      supply: c.supply,
      status: bad ? ("FAIL" as Status) : warn ? ("WARN" as Status) : ("PASS" as Status),
      runtime: `00:0${1 + Math.floor(r * 8)}.${Math.floor(r * 90)}`,
      gain: gain.toFixed(1),
      ugbw: ugbw.toFixed(1),
      pm: pm.toFixed(1),
      noise: (18.6 + r * 2.4).toFixed(2),
      power: (2.41 + (c.id === "SS" ? -0.5 : r * 0.2)).toFixed(2),
    };
  })
);

export const RUN_PLAN = [
  "Nominal sanity",
  "Process corners",
  "Voltage extremes",
  "Temperature sweep",
  "Monte Carlo",
  "Post-layout verification",
];

export const NOMINAL = [
  ["DC Gain", "67.41 dB"],
  ["Unity Gain Bandwidth", "184.2 MHz"],
  ["Phase Margin", "63.8 °"],
  ["CMRR", "91.2 dB"],
  ["PSRR+", "76.5 dB"],
  ["Input Noise", "18.63 µVrms"],
  ["Slew Rate +", "42.1 V/µs"],
  ["Slew Rate -", "38.4 V/µs"],
  ["Settling Time", "23.8 ns"],
  ["Static Power", "2.41 mW"],
  ["Area", "0.0139 mm²"],
];

export const POSTLAYOUT = [
  ["DC Gain", "64.82 dB", "-2.59"],
  ["UGBW", "162.7 MHz", "-21.5"],
  ["Phase Margin", "58.9 °", "-4.9"],
  ["Power", "2.44 mW", "+0.03"],
];

export const MARGINS: { name: string; margin: string; pct: number; status: Status }[] = [
  { name: "Gain", margin: "+7.4 dB", pct: 74, status: "PASS" },
  { name: "UGBW", margin: "+34 MHz", pct: 62, status: "PASS" },
  { name: "PM", margin: "+3.8°", pct: 38, status: "PASS" },
  { name: "Power", margin: "+0.09 mW", pct: 22, status: "PASS" },
  { name: "Swing", margin: "-40 mV", pct: 8, status: "FAIL" },
];

// ---------------------------------------------------------------- verification
export const DRC_VIOLATIONS = [
  {
    id: "001",
    rule: "M1.MIN.SPACE",
    layer: "M1",
    severity: "Error",
    x: 118.24,
    y: 82.11,
    text: "Metal1 spacing 0.085 µm < 0.090 µm",
  },
  {
    id: "002",
    rule: "VIA1.ENC",
    layer: "VIA1",
    severity: "Error",
    x: 122.91,
    y: 91.74,
    text: "Via1 enclosure by M2 0.010 µm < 0.015 µm",
  },
  {
    id: "003",
    rule: "POLY.MIN.WIDTH",
    layer: "POLY",
    severity: "Warning",
    x: 49.1,
    y: 61.83,
    text: "Poly width 0.055 µm < 0.060 µm",
  },
  {
    id: "004",
    rule: "M1.MIN.SPACE",
    layer: "M1",
    severity: "Error",
    x: 64.5,
    y: 44.2,
    text: "Metal1 spacing 0.081 µm < 0.090 µm",
  },
  {
    id: "005",
    rule: "DIFF.ENC.CONT",
    layer: "DIFF",
    severity: "Error",
    x: 210.3,
    y: 30.9,
    text: "Contact enclosure by diffusion violation",
  },
  {
    id: "006",
    rule: "NWELL.MIN.SPACE",
    layer: "NWELL",
    severity: "Warning",
    x: 88.7,
    y: 12.4,
    text: "Nwell spacing 0.58 µm < 0.60 µm",
  },
  {
    id: "007",
    rule: "M2.DENSITY",
    layer: "M2",
    severity: "Error",
    x: 155.0,
    y: 70.5,
    text: "Metal2 density 18.2% < 20%",
  },
];

export const LVS_SUMMARY = {
  schematic: { devices: 38, nets: 52, pins: 8 },
  layout: { devices: 38, nets: 52, pins: 8 },
};

export const PEX_SUMMARY = [
  ["Resistors generated", "1,482"],
  ["Capacitors generated", "3,761"],
  ["Coupling capacitors", "2,114"],
  ["Extracted nets", "52"],
  ["Runtime", "00:41"],
];

export const CONFIG_BINDINGS = [
  { inst: "/", cell: "ota_core", view: "schematic" },
  { inst: "XBIAS", cell: "bias_gen", view: "schematic" },
  { inst: "XCMFB", cell: "cmfb", view: "schematic" },
  { inst: "XOUTPUT", cell: "output_stage", view: "extracted" },
];

export const CONSTRAINTS = [
  {
    group: "Matching",
    items: [
      {
        id: "INPUT_PAIR",
        type: "Device Matching",
        members: ["M1", "M2"],
        orientation: "Mirrored",
        topology: "Common Centroid",
        dummies: "Required",
        mismatch: "0.5 %",
      },
      {
        id: "CURRENT_MIRROR_1",
        type: "Device Matching",
        members: ["M3", "M4"],
        orientation: "R0",
        topology: "Interdigitated",
        dummies: "Required",
        mismatch: "0.8 %",
      },
    ],
  },
  {
    group: "Symmetry",
    items: [
      {
        id: "OUTPUT_BRANCH",
        type: "Symmetry",
        members: ["M6", "M7", "M8"],
        orientation: "Mirror Y",
        topology: "Axial",
        dummies: "Optional",
        mismatch: "1.0 %",
      },
    ],
  },
  {
    group: "Routing",
    items: [
      {
        id: "VDD",
        type: "Power Route",
        members: ["M3", "M4", "M6"],
        orientation: "—",
        topology: "Mesh",
        dummies: "—",
        mismatch: "—",
      },
      {
        id: "VOUTP",
        type: "Shielded Route",
        members: ["M6", "M7"],
        orientation: "—",
        topology: "Coax",
        dummies: "—",
        mismatch: "—",
      },
    ],
  },
  {
    group: "Critical Nets",
    items: [
      {
        id: "VINP",
        type: "Critical Net",
        members: ["M1"],
        orientation: "—",
        topology: "Shielded",
        dummies: "—",
        mismatch: "—",
      },
      {
        id: "VINN",
        type: "Critical Net",
        members: ["M2"],
        orientation: "—",
        topology: "Shielded",
        dummies: "—",
        mismatch: "—",
      },
    ],
  },
];

export const TECH_DEVICES = [
  {
    name: "nmos_1v2",
    minL: "60 nm",
    vdd: "1.2 V",
    params: ["W", "L", "nf", "m", "ad", "as", "pd", "ps"],
  },
  {
    name: "pmos_1v2",
    minL: "60 nm",
    vdd: "1.2 V",
    params: ["W", "L", "nf", "m", "ad", "as", "pd", "ps"],
  },
  { name: "nmos_lvt", minL: "60 nm", vdd: "1.2 V", params: ["W", "L", "nf", "m"] },
  { name: "pmos_lvt", minL: "60 nm", vdd: "1.2 V", params: ["W", "L", "nf", "m"] },
  { name: "mimcap", minL: "2 µm", vdd: "1.2 V", params: ["w", "l", "c"] },
  { name: "polyres", minL: "0.4 µm", vdd: "1.2 V", params: ["w", "l", "r"] },
  { name: "nwellres", minL: "1 µm", vdd: "1.2 V", params: ["w", "l", "r"] },
  { name: "diode", minL: "0.2 µm", vdd: "1.2 V", params: ["area", "pj"] },
];

export const STACK = [
  "M6",
  "V5",
  "M5",
  "V4",
  "M4",
  "V3",
  "M3",
  "V2",
  "M2",
  "V1",
  "M1",
  "CONTACT",
  "POLY",
  "ACTIVE",
  "WELL",
  "SUBSTRATE",
];

export const REVISIONS = [
  { rev: "r142", msg: "Adjusted input pair W/L", who: "YS", when: "17:42" },
  { rev: "r141", msg: "Added compensation zero resistor", who: "YS", when: "16:19" },
  { rev: "r140", msg: "CMFB routing cleanup", who: "RK", when: "14:51" },
  { rev: "r139", msg: "Guard ring around input pair", who: "RK", when: "13:07" },
  { rev: "r138", msg: "Initial output stage sizing", who: "YS", when: "11:22" },
];

export const RUN_HISTORY = [
  {
    id: "1042",
    label: "Run 42",
    when: "Today 17:42",
    gain: "67.4",
    ugbw: "184",
    pm: "63.8",
    power: "2.41",
  },
  {
    id: "1041",
    label: "Run 41",
    when: "Today 17:30",
    gain: "65.8",
    ugbw: "171",
    pm: "66.2",
    power: "2.18",
  },
  {
    id: "1040",
    label: "Run 40",
    when: "Today 16:58",
    gain: "64.1",
    ugbw: "166",
    pm: "67.0",
    power: "2.04",
  },
  {
    id: "1039",
    label: "Run 39",
    when: "Today 16:12",
    gain: "62.9",
    ugbw: "158",
    pm: "68.4",
    power: "1.92",
  },
];

export const INITIAL_JOBS = [
  {
    id: "sim_1042",
    type: "AC",
    cell: "tb_ota_ac",
    host: "local",
    status: "Complete" as const,
    progress: 100,
    runtime: "00:13",
  },
  {
    id: "drc_812",
    type: "DRC",
    cell: "ota_core",
    host: "compute03",
    status: "Complete" as const,
    progress: 100,
    runtime: "00:42",
  },
  {
    id: "mc_221",
    type: "Monte Carlo",
    cell: "tb_ota_mc",
    host: "farm",
    status: "Queued" as const,
    progress: 0,
    runtime: "—",
  },
];

export const SEARCH_INDEX = [
  { kind: "Net", name: "VOUTP", where: "ota_core/schematic", ws: "schematic" },
  { kind: "Pin", name: "VOUTP", where: "ota_core/schematic", ws: "schematic" },
  { kind: "Pin", name: "VOUTP", where: "ota_core/layout", ws: "layout" },
  { kind: "Expression", name: "VOUTP", where: "tb_ota_tran", ws: "waveforms" },
  { kind: "Output", name: "VOUTP", where: "Simulation Explorer", ws: "sim" },
  { kind: "Net", name: "VOUTN", where: "ota_core/schematic", ws: "schematic" },
  { kind: "Instance", name: "M1", where: "ota_core/schematic", ws: "schematic" },
  { kind: "Instance", name: "M5", where: "ota_core/schematic", ws: "schematic" },
  { kind: "Cell", name: "bias_gen", where: "aurora_65", ws: "library" },
  { kind: "Rule", name: "M1.MIN.SPACE", where: "DRC results", ws: "pv" },
];
