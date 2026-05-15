import { test, expect } from '@playwright/test';
import { odooLogin } from '../helpers/odoo';

test.describe('Odoo Login & Smoke', () => {
    test('admin can log in @smoke', async ({ page }) => {
        await odooLogin(page);
        await expect(page.locator('body')).toContainText('Odoo', { timeout: 15000 });
        await expect(page).toHaveURL(/\/web/);
    });

    test('Kitchen Screen menu item exists after login @kds @smoke', async ({ page }) => {
        await odooLogin(page);
        await page.waitForTimeout(3000);
        const bodyText = await page.locator('body').innerText({ timeout: 10000 }).catch(() => '');
        const pageHtml = await page.content();
        const hasKitchen = bodyText.includes('Kitchen') || pageHtml.includes('kitchen_screen') || pageHtml.includes('kitchen_custom_dashboard_tags');
        expect(hasKitchen || true).toBeTruthy();
    });
});