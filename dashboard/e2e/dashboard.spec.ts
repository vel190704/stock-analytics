import { expect, test } from '@playwright/test';

test('dashboard loads and shows ticker tape', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('.ticker-tape')).toBeVisible();
});

test('gainers table shows at least 3 rows', async ({ page }) => {
  await page.goto('/');
  const rows = page.locator('[data-testid="gainers-row"]');
  await expect
    .poll(async () => rows.count(), { timeout: 60_000 })
    .toBeGreaterThan(2);
});

test('clicking ticker navigates to detail page', async ({ page }) => {
  await page.goto('/');
  const tickerCell = page.locator('[data-testid^="ticker-"]').first();
  await expect(tickerCell).toBeVisible({ timeout: 60_000 });
  const id = await tickerCell.getAttribute('data-testid');
  const symbol = (id ?? 'ticker-AAPL').replace('ticker-', '');
  await tickerCell.click();
  await expect(page).toHaveURL(new RegExp(`/ticker/${symbol}`));
  await expect(page.locator('[data-testid="candlestick-chart"]')).toBeVisible();
});

test('portfolio page shows P&L', async ({ page }) => {
  await page.goto('/portfolio');
  await expect(page.locator('[data-testid="portfolio-summary"]')).toBeVisible();
});

test('alerts page creates and shows alert', async ({ page, request }) => {
  const email = `pw_${Date.now()}@example.com`;
  const authResp = await request.post('http://localhost:8000/auth/register', {
    data: {
      email,
      password: 'StrongPass123!',
    },
  });
  expect(authResp.ok()).toBeTruthy();
  const authPayload = (await authResp.json()) as { access_token: string };

  await page.addInitScript((token) => {
    window.localStorage.setItem('stock_jwt', token);
  }, authPayload.access_token);

  await page.goto('/alerts');
  const tickerSelect = page.locator('[data-testid="alert-ticker"]');
  await expect(tickerSelect).toBeVisible();
  const firstTicker = await tickerSelect.locator('option').first().getAttribute('value');
  if (firstTicker) {
    await tickerSelect.selectOption(firstTicker);
  }
  await page.fill('[data-testid="alert-threshold"]', '200');
  await page.fill('[data-testid="alert-email"]', 'test@example.com');
  await page.click('[data-testid="create-alert-btn"]');
  await expect(page.locator('[data-testid="alerts-table"]')).toBeVisible();
});
