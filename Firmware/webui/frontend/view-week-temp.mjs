import { firefox } from 'playwright';

const browser = await firefox.launch({ headless: true });
const page = await browser.newPage();

await page.goto('http://localhost:5173/scheduler');
await page.waitForLoadState('networkidle');

await page.selectOption('select[aria-label="Select schedule"]', { label: 'Overnight Moth Survey' });
await page.waitForTimeout(1000);

await page.click('button:has-text("Week")');
await page.waitForTimeout(1500);

// Target the week timeline grid
const gridContainer = await page.locator('.border.border-gray-700.rounded-lg').first();
const grid = await gridContainer.locator('.grid').first();

const cells = await grid.locator('> div').all();

console.log('Header row:');
for (let i = 0; i < 8 && i < cells.length; i++) {
  const box = await cells[i].boundingBox();
  const text = (await cells[i].textContent()).trim().substring(0, 15);
  console.log('  [' + i + '] w=' + Math.round(box.width) + ', h=' + Math.round(box.height) + ' "' + text + '"');
}

// Check alignment
const cornerBox = await cells[0].boundingBox();
const header1Box = await cells[1].boundingBox();
console.log('\n--- Alignment Check ---');
console.log('Corner cell: h=' + Math.round(cornerBox.height));
console.log('Day 1 header: h=' + Math.round(header1Box.height));
if (Math.round(cornerBox.height) === Math.round(header1Box.height)) {
  console.log('✅ Heights match!');
} else {
  console.log('⚠️  HEIGHT MISMATCH');
}

// Take screenshot
await page.screenshot({ path: '/tmp/week-view-fixed.png', fullPage: true });
console.log('\nScreenshot saved to /tmp/week-view-fixed.png');

await browser.close();
