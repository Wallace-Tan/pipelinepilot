import { expect, test, type Page } from "@playwright/test";

async function assertAccessible(page: Page) {
  const violations = await page.evaluate(() => {
    const unnamedButtons = [...document.querySelectorAll("button")]
      .filter((button) => !(button.textContent?.trim() || button.getAttribute("aria-label") || button.getAttribute("title")))
      .map((button) => button.outerHTML.slice(0, 120));
    const unnamedInputs = [...document.querySelectorAll("input, textarea")]
      .filter((field) => !(field.getAttribute("aria-label") || field.getAttribute("aria-labelledby") || field.closest("label")))
      .map((field) => field.outerHTML.slice(0, 120));
    return { unnamedButtons, unnamedInputs };
  });
  expect(violations).toEqual({ unnamedButtons: [], unnamedInputs: [] });
}

test("landing page introduces the evidence constellation and enters the system", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "When pipelines fail, decisions should be explainable." })).toBeVisible();
  await expect(page.getByRole("button", { name: "Open Command Center" }).first()).toBeVisible();
  await expect(page.getByRole("button", { name: /Airflow/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /dbt/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Snowflake/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Monitoring/ })).toBeVisible();
  await page.getByRole("button", { name: /Airflow/ }).click();
  await expect(page.getByText("Airflow · Failure signature", { exact: true })).toBeVisible();
  await expect(page.getByText(/ColumnNotFound: order_channel/)).toBeVisible();
  await assertAccessible(page);

  await page.getByRole("button", { name: "Open Command Center" }).first().click();
  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByRole("heading", { name: "Command Center" })).toBeVisible();
});

test("landing route supports direct system entry and browser back", async ({ page }) => {
  await page.goto("/app");
  await expect(page.getByRole("heading", { name: "Command Center" })).toBeVisible();
  await page.goto("/");
  await page.getByRole("button", { name: "Open Command Center" }).first().click();
  await page.goBack();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: "When pipelines fail, decisions should be explainable." })).toBeVisible();
});

test("constellation respects reduced motion and stays within a narrow viewport", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "When pipelines fail, decisions should be explainable." })).toBeVisible();
  await expect(page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).resolves.toBe(true);
  await expect(page.locator(".constellation-scene")).toHaveCSS("transform", "none");
  await assertAccessible(page);
});

test("governed recovery lifecycle and accessible controls remain operable", async ({ page }) => {
  await page.goto("/app");
  await assertAccessible(page);

  await page.getByRole("button", { name: /Reset fixture/ }).click();
  await expect(page.getByRole("button", { name: "Open workbench" })).toBeVisible();
  await page.getByRole("button", { name: "Open workbench" }).click();
  await page.getByRole("button", { name: "Investigate fixture incident" }).click();
  await expect(page.getByText("Evidence collected")).toBeVisible();
  await assertAccessible(page);

  await page.getByRole("button", { name: /Try execution/ }).click();
  await expect(page.getByText(/approval_required:/)).toBeVisible();
  await page.getByRole("button", { name: "Approve fixture recovery" }).click();
  await expect(page.getByRole("button", { name: "Execute fixture recovery" })).toBeVisible();
  await page.getByRole("button", { name: "Execute fixture recovery" }).click();
  await page.getByRole("button", { name: "Validate recovery" }).click();
  await expect(page.getByText("Validated", { exact: true }).first()).toBeVisible();

  await page.getByRole("button", { name: "Overview" }).click();
  await expect(page.getByText("Healthy", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("daily_store_revenue", { exact: true }).first()).toBeVisible();
  await assertAccessible(page);

  await page.getByRole("button", { name: "Agent detail" }).click();
  await expect(page.getByRole("heading", { name: "Agent detail" })).toBeVisible();
  await page.getByRole("button", { name: "Execution detail" }).click();
  await expect(page.getByRole("heading", { name: "Execution detail" })).toBeVisible();
  await assertAccessible(page);
});

test("exception queue filters seeded records", async ({ page }) => {
  await page.goto("/app");
  await expect(page.getByRole("region", { name: "Exception queue" })).toBeVisible();
  await page.getByRole("button", { name: /Reset fixture/ }).click();
  await expect(page.getByRole("button", { name: "Open workbench" })).toBeVisible();
  await page.getByRole("button", { name: "Resolved" }).click();
  await expect(page.getByText("customer_freshness_hourly", { exact: true })).toBeVisible();
  await expect(page.getByText("warehouse_permissions_check", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Open" }).click();
  await expect(page.getByText("retail_orders_daily", { exact: true })).toBeVisible();
});

test("approval gate rejects recovery and closes the action path", async ({ page }) => {
  await page.goto("/app");
  await page.getByRole("button", { name: /Reset fixture/ }).click();
  await page.getByRole("button", { name: "Open workbench" }).click();
  await page.getByRole("button", { name: "Investigate fixture incident" }).click();
  await expect(page.getByRole("button", { name: /Try execution/ })).toBeVisible();

  await page.getByRole("button", { name: /Try execution/ }).click();
  await expect(page.getByText(/approval_required:/)).toBeVisible();
  await page.getByRole("button", { name: "Reject recovery" }).click();

  await expect(page.locator(".state-value")).toHaveText("Denied");
  await expect(page.getByRole("button", { name: "Approve fixture recovery" })).toHaveCount(0);
  await assertAccessible(page);
});

test("edited proposals remain visible in the approval record", async ({ page }) => {
  await page.goto("/app");
  await page.getByRole("button", { name: /Reset fixture/ }).click();
  await page.getByRole("button", { name: "Open workbench" }).click();
  await page.getByRole("button", { name: "Investigate fixture incident" }).click();
  await expect(page.getByRole("button", { name: "Edit proposal" })).toBeVisible();

  const editedAction = "Replay the corrected staging model and refresh downstream reporting";
  await page.getByRole("button", { name: "Edit proposal" }).click();
  await page.getByRole("textbox", { name: "Edit proposed action" }).fill(editedAction);
  await page.getByRole("button", { name: /Save proposed action/ }).click();
  await page.getByRole("button", { name: "Approve fixture recovery" }).click();
  await expect(page.getByText(new RegExp(`Approve edited recovery plan: ${editedAction}`)).first()).toBeVisible();
  await assertAccessible(page);
});

test("read-only views, search empty state, and narrow layout remain usable", async ({ page }) => {
  await page.setViewportSize({ width: 910, height: 698 });
  await page.goto("/app");
  await page.getByRole("button", { name: /Reset fixture/ }).click();

  for (const view of ["Agent detail", "Execution detail", "Runbooks", "Policy", "Audit log"]) {
    await page.getByRole("button", { name: new RegExp(`^${view}`) }).click();
    await expect(page.getByRole("heading", { name: view })).toBeVisible();
  }

  await page.getByRole("button", { name: "Search" }).click();
  await page.getByRole("textbox", { name: "Search workspace" }).fill("no-such-workspace-record");
  await expect(page.getByText("No workspace matches.", { exact: true })).toBeVisible();
  await expect(page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).resolves.toBe(true);
  await assertAccessible(page);
});

test("API outage exposes a retryable error without breaking the shell", async ({ page }) => {
  await page.route("**/v1/demo/status", async (route) => {
    await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ error: "unavailable" }) });
  });
  await page.goto("/app");

  await expect(page.getByRole("alert")).toContainText("Demo readiness status is unavailable.");
  await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Command Center" })).toBeVisible();
  await assertAccessible(page);
});
