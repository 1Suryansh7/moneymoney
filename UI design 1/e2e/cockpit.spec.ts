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

    // 4. Verify NewCellDialog opened
    await expect(page.getByText("New Cell View")).toBeVisible();

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

    // 8. Wait for dialog to close on success
    await expect(page.getByText("New Cell View")).not.toBeVisible({ timeout: 10000 });

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
    await expect(page.getByText("New Cell View")).not.toBeVisible({ timeout: 10000 });

    const schemTab = page.getByRole("tab", { name: "schem_live_test : schematic" });
    await expect(schemTab).toBeVisible({ timeout: 10000 });
    await schemTab.click();

    const canvas = page.locator('svg[aria-label="Schematic canvas"]');
    await expect(canvas.getByText("m1", { exact: true })).toBeVisible({ timeout: 10000 });
    await expect(canvas.getByText("m2", { exact: true })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("2 instances")).toBeVisible();
    await expect(page.getByText("schem_live_test : schematic — sky130 — auto-layout")).toBeVisible();
  });
});
