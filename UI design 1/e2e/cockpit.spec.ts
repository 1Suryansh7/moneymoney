import { test, expect } from "@playwright/test";

test.describe("OpenVirtuoso Web Cockpit E2E Tests", () => {
  test("loads cockpit, runs CMOS inverter simulation, and verifies waveform rendering", async ({
    page,
  }) => {
    test.slow(); // real ngspice sims behind Run + measure: ~2min on shared hardware
    page.on("console", (msg) => console.log(`BROWSER ${msg.type()}: ${msg.text()}`));
    page.on("pageerror", (err) => console.log(`BROWSER PAGEERROR: ${err}`));
    // 1. Open the UI
    await page.goto("http://localhost:5173", { waitUntil: "networkidle" });

    // 2. Click on the Simulation Explorer tab
    const simTab = page.getByRole("tab", { name: "Simulation Explorer" });
    await expect(simTab).toBeVisible({ timeout: 10000 });
    await simTab.click();

    // 3. Find and click the exact 'Run' simulation button in the toolbar
    const runBtn = page.getByRole("button", { name: "Run", exact: true }).first();
    await expect(runBtn).toBeVisible({ timeout: 10000 });
    await runBtn.click();

    // 4. Wait for the simulation phase to transition to COMPLETE in the Live Run table
    const phaseCell = page.locator("tr:has(td:text-is('Phase')) td").nth(1);
    await expect(phaseCell).toHaveText("COMPLETE", { timeout: 60000 });

    // Verify Points count is populated (not em-dash)
    const pointsCell = page.locator("tr:has(td:text-is('Points')) td").nth(1);
    await expect(pointsCell).not.toHaveText("—");
    const pointsCount = await pointsCell.innerText();
    console.log("Simulation complete with data points:", pointsCount);

    // 4b. Outputs table shows the measured DC gain (R0-4b: live measure,
    // not NOT RUN). Measure runs two sims behind the route on shared
    // hardware: allow 300s.
    const gainRow = page.locator("tr:has(td:text-is('DC Gain'))");
    await expect(gainRow).toContainText("V/V", { timeout: 300000 });
    await expect(gainRow).toContainText("MEASURED", { timeout: 5000 });
    console.log("Measured gain row:", await gainRow.innerText());

    // 4c. Bandwidth row shows loaded UGBW in the result cell (R0-4e
    // declared 1 pF). NOTE: match the result cell (nth 2), not the row:
    // the static spec column always contains "MHz".
    const bwResult = page.locator("tr:has(td:text-is('UGBW')) td").nth(2);
    await expect(bwResult).toContainText("MHz", { timeout: 300000 });
    const bwRow = page.locator("tr:has(td:text-is('UGBW'))");
    await expect(bwRow).toContainText("MEASURED", { timeout: 300000 });
    console.log("Measured bandwidth row:", await bwRow.innerText());

    // 5. Navigate to Waveform Analyzer
    const waveTab = page.getByRole("tab", { name: "Waveform Analyzer" });
    await expect(waveTab).toBeVisible({ timeout: 10000 });
    await waveTab.click();

    // 6. Verify SVG waveform plots are rendered
    const svgPlot = page.locator("svg").first();
    await expect(svgPlot).toBeVisible({ timeout: 10000 });

    // Verify waveform trace polylines exist inside the SVG
    const tracePolylines = page.locator("svg polyline");
    await expect(tracePolylines.first()).toBeVisible({ timeout: 10000 });
    const polylineCount = await tracePolylines.count();
    expect(polylineCount).toBeGreaterThan(0);
    console.log("Found waveform polylines:", polylineCount);

    // Verify Results Browser and Legend are populated
    await expect(page.locator("text=Results Browser")).toBeVisible();
    await expect(page.locator("text=Legend")).toBeVisible();

    // 7. Save verification screenshot
    await page.screenshot({ path: "cockpit_simulation_verified.png", fullPage: true });
    console.log("Screenshot saved to cockpit_simulation_verified.png");
  });

  test("creates a common_source cell via NewCellDialog and verifies live creation", async ({
    page,
  }) => {
    // 1. Open the UI
    await page.goto("http://localhost:5173", { waitUntil: "networkidle" });

    // 2. Open File menu
    const fileTrigger = page.locator("[role=menubar] button, [role=menuitem]").filter({ hasText: /^File$/ }).first();
    await fileTrigger.click();

    // 3. Click "New Cell View..."
    const newCellItem = page.getByText("New Cell View...");
    await expect(newCellItem).toBeVisible();
    await newCellItem.click();

    // 4. Verify NewCellDialog opened (scoped to the dialog role: the
    // canvas empty state mentions the menu path as guidance text)
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 10000 });

    // 5. Fill cell name
    const cellInput = page.getByPlaceholder("e.g. my_amp");
    await cellInput.fill("cs_amp_test");

    // 6. Select "common_source" template (scoped to the dialog: the
    // schematic toolbar now hosts its own cell-picker select)
    const templateSelect = page.getByLabel("Template");
    await templateSelect.selectOption("common_source");

    // 7. Click "Create"
    const createBtn = page.getByRole("button", { name: "Create" });
    await expect(createBtn).toBeEnabled();
    await createBtn.click();

    // 8. Wait for dialog to close on success (role-scoped: canvas
    // guidance text shares the menu-path wording)
    await expect(page.getByRole("dialog")).not.toBeVisible({ timeout: 10000 });

    // 9. Verify creation log in console dock
    const logEntry = page.locator("text=/Created my_project\\/cs_amp_test from common_source/i");
    await expect(logEntry).toBeVisible({ timeout: 5000 });

    // 10. Capture screenshot
    await page.screenshot({ path: "cockpit_cell_created.png", fullPage: true });
    console.log("Screenshot saved to cockpit_cell_created.png");
  });

  test("toolbar New Cell button opens the dialog (dead-button regression)", async ({
    page,
  }) => {
    // The toolbar icon shipped without an onClick: clicks fell into the
    // void. This pins the wire: toolbar button -> NewCellDialog visible.
    await page.goto("http://localhost:5173", { waitUntil: "networkidle" });
    const toolBtn = page.getByRole("button", { name: "New Cell View" });
    await expect(toolBtn).toBeVisible({ timeout: 10000 });
    await toolBtn.click();
    await expect(page.getByText("Backend sizing defaults apply.")).toBeVisible({
      timeout: 10000,
    });
  });

  test("created cell renders live schematic instances on the canvas", async ({
    page,
  }) => {
    // Full 3e loop: dialog -> named cell -> schematic tab shows its real
    // transistors (m1/m2) with live counts, not the ota_core mock.
    await page.goto("http://localhost:5173", { waitUntil: "networkidle" });
    await page.getByRole("button", { name: "New Cell View" }).click();
    await page.getByPlaceholder("e.g. my_amp").fill("schem_live_test");
    await page.getByLabel("Template").selectOption("common_source");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.getByRole("dialog")).not.toBeVisible({ timeout: 10000 });

    const schemTab = page.getByRole("tab", { name: "schem_live_test : schematic" });
    await expect(schemTab).toBeVisible({ timeout: 10000 });
    await schemTab.click();

    const canvas = page.locator('svg[aria-label="Schematic canvas"]');
    await expect(canvas.getByText("m1", { exact: true })).toBeVisible({ timeout: 10000 });
    await expect(canvas.getByText("m2", { exact: true })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("2 instances")).toBeVisible();
    await expect(page.getByText("schem_live_test : schematic — sky130 — auto-layout")).toBeVisible();
  });

  test("optimizer streams trials, cancels mid-run, then completes", async ({
    page,
  }) => {    test.slow(); // real sims behind every trial: ~10min on shared hardware
    await page.goto("http://localhost:5173", { waitUntil: "networkidle" });
    const simTab = page.getByRole("tab", { name: "Simulation Explorer" });
    await simTab.click();
    await page.getByRole("button", { name: "Run", exact: true }).first().click();
    const phaseCell = page.locator("tr:has(td:text-is('Phase')) td").nth(1);
    await expect(phaseCell).toHaveText("COMPLETE", { timeout: 120000 });

    // Start study, wait for the first trial to stream, then cancel.
    await page.getByRole("button", { name: "Optimize" }).click();
    const trialRows = page.locator("table:has(th:text-is('Trial')) tbody tr");
    await expect(trialRows.first()).toBeVisible({ timeout: 600000 });
    await page.getByRole("button", { name: "Stop Study" }).click();
    await expect(page.getByText("done · 1 trials")).toBeVisible({ timeout: 120000 });

    // Re-run to completion: 3 trials, best banner, convergence curve.
    await page.getByRole("button", { name: "Optimize" }).click();
    await expect(page.locator("table:has(th:text-is('Trial')) tbody tr")).toHaveCount(
      3,
      { timeout: 1200000 },
    );
    await expect(page.getByText(/Best: trial \d/)).toBeVisible({ timeout: 10000 });
    const svgPlot = page.locator("svg").first();
    await expect(svgPlot).toBeVisible({ timeout: 10000 });
  });

  test("corner sweep runs the envelope and shows per-corner rows", async ({ page }) => {
    test.slow(); // five ngspice sims behind one button: ~2min on shared hardware
    await page.goto("http://localhost:5173", { waitUntil: "networkidle" });
    const simTab = page.getByRole("tab", { name: "Simulation Explorer" });
    await simTab.click();

    // Run All Corners previously called the nominal sim (miswired): it
    // must now drive POST /corners/run for the checked envelope ids.
    await page.getByRole("button", { name: "Run All Corners" }).click();

    // Five per-corner rows render with backend truth (temp + supply +
    // status); the sweep log line proves completion.
    await expect(page.getByText("Corners done: 5/5 succeeded")).toBeVisible({
      timeout: 600000,
    });
    for (const id of ["TT", "FF", "SS", "FS", "SF"]) {
      await expect(
        page.getByRole("button", { name: new RegExp(`${id}.*succeeded`) }),
      ).toBeVisible({ timeout: 10000 });
    }

    // Clicking a corner row shows its wave in the analyzer (display
    // routing through the shared liveWave state).
    await page.getByRole("button", { name: /SS.*succeeded/ }).click();
    const waveTab = page.getByRole("tab", { name: "Waveform Analyzer" });
    await waveTab.click();
    const tracePolylines = page.locator("svg polyline");
    await expect(tracePolylines.first()).toBeVisible({ timeout: 10000 });
    expect(await tracePolylines.count()).toBeGreaterThan(0);
  });

  test("pre/post comparison renders the degradation table", async ({ page }) => {
    test.slow(); // emit + extract + four ngspice sims behind one button: ~3min
    await page.goto("http://localhost:5173", { waitUntil: "networkidle" });
    const simTab = page.getByRole("tab", { name: "Simulation Explorer" });
    await simTab.click();

    await page.getByRole("button", { name: "Compare Pre/Post" }).click();

    // Table renders measured pre/post rows plus the UGB drop percentage
    // ("UGB drop" is unique to the Pre/Post table — the Outputs table
    // has its own DC Gain/UGBW rows).
    await expect(page.getByRole("cell", { name: "UGB drop", exact: true })).toBeVisible({
      timeout: 600000,
    });
    const dropRow = page.locator("tr:has(td:text-is('UGB drop'))");
    await expect(dropRow).toContainText("%", { timeout: 5000 });
    await expect(dropRow).toContainText("MEASURED", { timeout: 5000 });
    const prepostTable = dropRow.locator("xpath=ancestor::table[1]");
    await expect(prepostTable).toContainText("V/V", { timeout: 5000 });
    await expect(prepostTable).toContainText("MHz", { timeout: 5000 });
  });

  test("UI cell creation produces canonical netlist equivalent to direct engine API", async ({
    page,
    request,
  }) => {
    const testCellName = `equiv_cs_${Date.now()}`;

    // 1. Open the UI
    await page.goto("http://localhost:5173", { waitUntil: "networkidle" });

    // 2. Open New Cell View dialog via toolbar button
    await page.getByRole("button", { name: "New Cell View" }).click();
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 10000 });

    // 3. Create common_source cell via the UI dialog
    await page.getByPlaceholder("e.g. my_amp").fill(testCellName);
    await page.getByLabel("Template").selectOption("common_source");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.getByRole("dialog")).not.toBeVisible({ timeout: 10000 });

    // 4. Find the cell ID created by the UI from the GET /cells API
    const cellsResp = await request.get("http://localhost:8000/cells");
    expect(cellsResp.ok()).toBeTruthy();
    const cells = (await cellsResp.json()) as { cell_id: string; cell_name: string }[];
    const uiCell = cells.find((c) => c.cell_name === testCellName);
    expect(uiCell).toBeDefined();
    const uiCellId = uiCell!.cell_id;

    // 5. Compile netlist for UI-created cell via POST /netlist
    const uiNetlistResp = await request.post("http://localhost:8000/netlist", {
      data: { cell_id: uiCellId },
    });
    expect(uiNetlistResp.ok()).toBeTruthy();
    const uiNetlist = ((await uiNetlistResp.json()) as { netlist: string }).netlist;

    // 6. Independently create the identical cell purely through the Engine API
    const apiProjResp = await request.post("http://localhost:8000/projects", {
      data: { name: "api_equiv_proj" },
    });
    const apiProjId = ((await apiProjResp.json()) as { project_id: string }).project_id;
    const apiAnchorResp = await request.post("http://localhost:8000/cells", {
      data: { project_id: apiProjId, cell_name: `${testCellName}_api_anchor` },
    });
    const apiAnchorId = ((await apiAnchorResp.json()) as { cell_id: string }).cell_id;
    const apiInstResp = await request.post("http://localhost:8000/instantiate", {
      data: { cell_id: apiAnchorId, template_id: "common_source", parameters: {} },
    });
    const apiInstId = ((await apiInstResp.json()) as { cell_id: string }).cell_id;
    await request.post(`http://localhost:8000/cells/${encodeURIComponent(apiInstId)}/rename`, {
      data: { cell_name: testCellName },
    });

    // 7. Compile netlist for API-created cell via POST /netlist
    const apiNetlistResp = await request.post("http://localhost:8000/netlist", {
      data: { cell_id: apiInstId },
    });
    expect(apiNetlistResp.ok()).toBeTruthy();
    const apiNetlist = ((await apiNetlistResp.json()) as { netlist: string }).netlist;

    // 8. Assert byte-identical netlist equality between UI-instantiated and API-instantiated designs
    expect(uiNetlist).toBe(apiNetlist);

    // 9. Assert expected electrical instances and Sky130 model bindings exist in both
    expect(uiNetlist).toContain("Xm1 out in vss vss sky130_fd_pr__nfet_01v8");
    expect(uiNetlist).toContain("Xm2 out vbias vdd vdd sky130_fd_pr__pfet_01v8");
    expect(uiNetlist).toContain(".end");
  });
});




