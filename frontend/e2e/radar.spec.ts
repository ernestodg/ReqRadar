import { expect, test } from "@playwright/test";
import path from "node:path";

function generatedCsv(label: string) {
  return [
    "Requirement ID,Type,Title,Description,Status,Parent ID,Related To,Tags,Owner",
    `${label}-001,Requirement,${label} title 1,${label} description 1,Active,,,,Owner`,
    `${label}-002,Requirement,${label} title 2,${label} description 2,Active,,,,Owner`,
    `${label}-003,Requirement,${label} title 3,${label} description 3,Active,,,,Owner`,
  ].join("\n");
}

test("complete ReqRadar MVP workflow", async ({ page }) => {
  await page.setExtraHTTPHeaders({ "x-dev-user-id": `playwright-e2e-${Date.now()}` });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "ReqRadar" })).toBeVisible();
  await expect(page.getByText("Dev", { exact: true })).toBeVisible();

  const projectName = `E2E ${Date.now()}`;
  await page.getByTestId("project-name").fill(projectName);
  await page.getByTestId("create-project").click();
  await expect(page.getByText("requirements · V1 → V2")).toBeVisible();

  await page.getByTestId("csv-upload").setInputFiles(path.resolve("../sample-data/requirements-v1.csv"));
  await page.getByTestId("version-label").fill("V1");
  await expect(page.getByTestId("validation-messages")).toContainText("Requirement ID and Title mapped");
  await page.getByTestId("import-csv").click();
  await expect(page.locator(".imports-section")).toContainText("requirements-v1.csv");

  await page.getByTestId("csv-upload").setInputFiles(path.resolve("../sample-data/requirements-v2.csv"));
  await expect(page.getByTestId("validation-messages")).toContainText("requirements-v2.csv ready for mapping");
  await page.getByTestId("version-label").fill("V2");
  await page.getByTestId("import-csv").click();
  await expect(page.locator(".imports-section")).toContainText("requirements-v2.csv");

  await page.getByTestId("compare-versions").click();
  await expect(page.locator(".summary-grid")).toContainText("MODIFIED");
  await expect(page.locator(".summary-grid")).toContainText("16");
  await expect(page.getByTestId("project-breadcrumb")).toHaveText(projectName);
  await expect(page.getByText("Comparison V1 → V2")).toBeVisible();

  await page.getByTestId("change-filter").selectOption("MODIFIED");
  await page.getByTestId("severity-filter").selectOption("ALL");
  await page.getByTestId("change-row").first().click();
  await expect(page.getByTestId("change-diff")).toBeVisible();
  await expect(page.getByTestId("impact-finding").first()).toContainText("Confidence");

  await page.getByTestId("confirm-finding").click();
  await expect(page.getByText("CONFIRMED").first()).toBeVisible();
  await page.getByTestId("dismiss-finding").click();
  await expect(page.getByText("DISMISSED").first()).toBeVisible();
  await page.getByTestId("severity-override").selectOption("LOW");
  await page.getByTestId("reviewer-note").fill("E2E reviewed");
  await expect(page.getByTestId("reviewer-note")).toHaveValue("E2E reviewed");
  await page.getByTestId("save-note").click();
  await expect(page.getByTestId("reviewer-note")).toHaveValue("E2E reviewed");

  await page.getByTestId("back-to-history").click();
  await expect(page.getByRole("heading", { name: "Comparison History" })).toBeVisible();
  await expect(page.getByTestId("comparison-history-row").first()).toContainText("V1 → V2");
  await expect(page.getByRole("heading", { name: projectName })).toBeVisible();
  await expect(page.getByText("Dev", { exact: true })).toBeVisible();

  await page.getByTestId("csv-upload").setInputFiles({
    name: "requirements-v3.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(generatedCsv("REQ-E2E-V3")),
  });
  await page.getByTestId("version-label").fill("V3");
  await page.getByTestId("import-csv").click();
  await expect(page.locator(".imports-section")).toContainText("requirements-v3.csv");

  await page.getByTestId("compare-versions").click();
  await expect(page.getByText("Comparison V2 → V3")).toBeVisible();
  await page.getByTestId("project-breadcrumb").click();
  await expect(page.getByRole("heading", { name: "Comparison History" })).toBeVisible();
  await expect(page.getByTestId("comparison-history-row")).toHaveCount(2);
  await expect(page.getByTestId("comparison-history-row").first()).toContainText("V2 → V3");
  await expect(page.getByTestId("comparison-history-row").nth(1)).toContainText("V1 → V2");

  await page.getByTestId("comparison-history-row").nth(1).click();
  await expect(page.getByText("Comparison V1 → V2")).toBeVisible();
  await expect(page.getByTestId("project-breadcrumb")).toHaveText(projectName);
  await expect(page.getByText("Dev", { exact: true })).toBeVisible();

  const downloadCsv = page.waitForEvent("download");
  await page.getByTestId("export-csv").click();
  expect((await downloadCsv).suggestedFilename()).toContain(".csv");
  const downloadPdf = page.waitForEvent("download");
  await page.getByTestId("export-report").click();
  await page.getByTestId("export-audit-pdf").click();
  expect((await downloadPdf).suggestedFilename()).toContain("full-audit-report.pdf");
});
