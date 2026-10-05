import { expect, test } from "@playwright/test";
import path from "node:path";

test("complete ReqRadar MVP workflow", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Requirements Impact Radar")).toBeVisible();
  await expect(page.getByText("Dev auth active")).toBeVisible();

  await page.getByTestId("project-name").fill(`E2E ${Date.now()}`);
  await page.getByTestId("create-project").click();
  await expect(page.getByText("Upload two CSV versions")).toBeVisible();

  await page.getByTestId("csv-upload").setInputFiles(path.resolve("../sample-data/requirements-v1.csv"));
  await page.getByTestId("version-label").fill("V1");
  await expect(page.getByTestId("validation-messages")).toContainText("Requirement ID and Title mapped");
  await page.getByTestId("import-csv").click();
  await expect(page.getByText("V1")).toBeVisible();

  await page.getByTestId("csv-upload").setInputFiles(path.resolve("../sample-data/requirements-v2.csv"));
  await page.getByTestId("version-label").fill("V2");
  await page.getByTestId("import-csv").click();
  await expect(page.getByText("V2")).toBeVisible();

  await page.getByTestId("compare-versions").click();
  await expect(page.getByText("MODIFIED")).toBeVisible();
  await expect(page.getByText("16")).toBeVisible();

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
  await page.getByTestId("save-note").click();
  await expect(page.getByText("E2E reviewed")).toBeVisible();

  const downloadCsv = page.waitForEvent("download");
  await page.getByTestId("export-csv").click();
  expect((await downloadCsv).suggestedFilename()).toContain(".csv");
  const downloadPdf = page.waitForEvent("download");
  await page.getByTestId("export-pdf").click();
  expect((await downloadPdf).suggestedFilename()).toContain(".pdf");
});
