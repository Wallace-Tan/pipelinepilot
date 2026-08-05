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

test("governed recovery lifecycle and accessible controls remain operable", async ({ page }) => {
  await page.goto("/");
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
  await page.goto("/");
  await expect(page.getByRole("region", { name: "Exception queue" })).toBeVisible();
  await page.getByRole("button", { name: /Reset fixture/ }).click();
  await expect(page.getByRole("button", { name: "Open workbench" })).toBeVisible();
  await page.getByRole("button", { name: "Resolved" }).click();
  await expect(page.getByText("customer_freshness_hourly", { exact: true })).toBeVisible();
  await expect(page.getByText("warehouse_permissions_check", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Open" }).click();
  await expect(page.getByText("retail_orders_daily", { exact: true })).toBeVisible();
});
