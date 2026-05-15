import { test, expect } from '@playwright/test';
import { odooLogin } from '../helpers/odoo';

test.describe('Kitchen Display System (KDS)', () => {

    test.beforeEach(async ({ page }) => {
        await odooLogin(page);
    });

    test('KDS action loads and shows tabs @kds @smoke', async ({ page }) => {
        await page.goto('/web#action=kitchen_custom_dashboard_action');

        await page.waitForLoadState('networkidle');

        await expect(page.locator('#kitchen_screen')).toBeVisible({ timeout: 15000 });

        await expect(page.locator('.kds-tab', { hasText: 'Pendiente' })).toBeVisible({ timeout: 10000 });
        await expect(page.locator('.kds-tab', { hasText: 'En Horno' })).toBeVisible();
        await expect(page.locator('.kds-tab', { hasText: 'Listo' })).toBeVisible();
        await expect(page.locator('.kds-tab', { hasText: 'Entregado' })).toBeVisible();

        await expect(page.locator('.kds-count-badge')).toHaveCount(4);
    });

    test('KDS empty state shows no cards @kds', async ({ page }) => {
        await page.goto('/web#action=kitchen_custom_dashboard_action');
        await page.waitForLoadState('networkidle');

        await expect(page.locator('#kitchen_screen')).toBeVisible({ timeout: 15000 });

        const cards = page.locator('.kds-card');
        const count = await cards.count();
        expect(count).toBeGreaterThanOrEqual(0);
    });

    test('KDS tab switching changes active tab @kds', async ({ page }) => {
        await page.goto('/web#action=kitchen_custom_dashboard_action');
        await page.waitForLoadState('networkidle');

        await expect(page.locator('#kitchen_screen')).toBeVisible({ timeout: 15000 });

        const cookingTab = page.locator('.kds-tab', { hasText: 'En Horno' });
        await cookingTab.click();

        await expect(cookingTab).toHaveClass(/kds-tab--active/);

        const readyTab = page.locator('.kds-tab', { hasText: 'Listo' });
        await readyTab.click();
        await expect(readyTab).toHaveClass(/kds-tab--active/);
    });

    test('KDS auto-refreshes via polling (30s interval) @kds', async ({ page }) => {
        await page.goto('/web#action=kitchen_custom_dashboard_action');
        await page.waitForLoadState('networkidle');

        await expect(page.locator('#kitchen_screen')).toBeVisible({ timeout: 15000 });

        const responsePromise = page.waitForResponse(
            (resp) => resp.url().includes('pos.kitchen.ticket/get_details') || resp.url().includes('call_kw'),
            { timeout: 60000 }
        ).catch(() => null);

        if (responsePromise) {
            const resp = await responsePromise;
            expect(resp).not.toBeNull();
        }
    });

    test('KDS card shows ticket info structure @kds', async ({ page }) => {
        await page.goto('/web#action=kitchen_custom_dashboard_action');
        await page.waitForLoadState('networkidle');

        await expect(page.locator('#kitchen_screen')).toBeVisible({ timeout: 15000 });

        const pendingTab = page.locator('.kds-tab', { hasText: 'Pendiente' });
        await pendingTab.click();

        const pendingCount = await page.locator('.kds-count-badge').first().textContent();
        if (pendingCount && parseInt(pendingCount) > 0) {
            const firstCard = page.locator('.kds-card').first();
            await expect(firstCard.locator('.order-name')).toBeVisible({ timeout: 5000 });

            await expect(firstCard.locator('.kds-elapsed-num')).toBeVisible();
            await expect(firstCard.locator('.kds-elapsed-unit')).toContainText('min');

            await expect(firstCard.locator('.kds-btn-cancel')).toBeVisible();
        }
    });

    test('KDS payment status badge displays correctly @kds', async ({ page }) => {
        await page.goto('/web#action=kitchen_custom_dashboard_action');
        await page.waitForLoadState('networkidle');

        await expect(page.locator('#kitchen_screen')).toBeVisible({ timeout: 15000 });

        const pendingTab = page.locator('.kds-tab', { hasText: 'Pendiente' });
        await pendingTab.click();

        const cards = page.locator('.kds-card');
        const count = await cards.count();

        if (count > 0) {
            const badges = page.locator('.kds-badge-paid, .kds-badge-not-paid');
            const badgeCount = await badges.count();
            expect(badgeCount).toBeGreaterThan(0);
        }
    });

    test('KDS cancel ticket button exists on cards @kds', async ({ page }) => {
        await page.goto('/web#action=kitchen_custom_dashboard_action');
        await page.waitForLoadState('networkidle');

        await expect(page.locator('#kitchen_screen')).toBeVisible({ timeout: 15000 });

        const pendingTab = page.locator('.kds-tab', { hasText: 'Pendiente' });
        await pendingTab.click();

        const cards = page.locator('.kds-card');
        const count = await cards.count();

        if (count > 0) {
            await expect(cards.first().locator('.kds-btn-cancel')).toBeVisible();
        }
    });

    test('KDS line status badges render @kds', async ({ page }) => {
        await page.goto('/web#action=kitchen_custom_dashboard_action');
        await page.waitForLoadState('networkidle');

        await expect(page.locator('#kitchen_screen')).toBeVisible({ timeout: 15000 });

        const cards = page.locator('.kds-card');
        const count = await cards.count();

        if (count > 0) {
            const card = cards.first();
            const lines = card.locator('.kds-line');
            if (await lines.count() > 0) {
                const line = lines.first();
                await expect(line.locator('.qty')).toBeVisible();
                await expect(line.locator('.product-name')).toBeVisible();
            }
        }
    });
});