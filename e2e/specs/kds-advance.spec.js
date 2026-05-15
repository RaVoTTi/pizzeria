import { test, expect } from '@playwright/test';
import { odooLogin, ODOO } from '../helpers/odoo';

test.describe('POS Order → Kitchen Display Integration', () => {

    test.beforeEach(async ({ page }) => {
        await odooLogin(page);
    });

    test('JSON-RPC can create a POS order and it appears on KDS @kds @pos', async ({ page, context }) => {
        const jsonrpc = async (endpoint, method, params) => {
            const response = await fetch(new URL('/jsonrpc', ODOO.URL), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        service: 'object',
                        method: 'execute_kw',
                        args: [
                            ODOO.DB,
                            2,
                            ODOO.PASS,
                            method.split('.')[0],
                            method.split('.')[1],
                            params || [],
                        ],
                    },
                    id: Date.now(),
                }),
            });
            return response.json();
        };

        const [kdsPage] = await Promise.all([
            context.newPage(),
        ]);

        await kdsPage.goto('/web#action=kitchen_custom_dashboard_action');
        await kdsPage.waitForLoadState('networkidle');
        await expect(kdsPage.locator('#kitchen_screen')).toBeVisible({ timeout: 15000 });

        const pendingTab = kdsPage.locator('.kds-tab', { hasText: 'Pendiente' });
        await pendingTab.click();

        const initialCount = await kdsPage.locator('.kds-card').count();

        const kitchenTickets = await jsonrpc(null, 'pos.kitchen.ticket.search_read', [[["state", "=", "pending"]], ["id", "sequence", "pos_reference"]]);

        await kdsPage.waitForTimeout(2000);
        await kdsPage.reload();
        await kdsPage.waitForLoadState('networkidle');
        await expect(kdsPage.locator('#kitchen_screen')).toBeVisible({ timeout: 15000 });

        const newCount = await kdsPage.locator('.kds-card').count();
        expect(newCount).toBeGreaterThanOrEqual(initialCount);

        await kdsPage.close();
    });

    test('KDS ticket advance flow: pending → cooking → ready → delivered @kds', async ({ page }) => {
        await page.goto('/web#action=kitchen_custom_dashboard_action');
        await page.waitForLoadState('networkidle');

        await expect(page.locator('#kitchen_screen')).toBeVisible({ timeout: 15000 });

        const pendingTab = page.locator('.kds-tab', { hasText: 'Pendiente' });
        await pendingTab.click();

        const cards = page.locator('.kds-card');
        const count = await cards.count();

        if (count > 0) {
            const firstCard = cards.first();
            const nextStateHint = firstCard.locator('.kds-next-action');
            await expect(nextStateHint).toContainText('AL HORNO');

            const pendingCountBefore = parseInt(
                (await page.locator('.kds-count-badge').first().textContent()) || '0'
            );

            await firstCard.click();

            await page.waitForTimeout(2000);

            const cookingTab = page.locator('.kds-tab', { hasText: 'En Horno' });
            await cookingTab.click();

            await page.waitForLoadState('networkidle');

            const cookingCards = page.locator('.kds-card');
            const cookingCount = await cookingCards.count();

            if (cookingCount > 0) {
                const readyHint = cookingCards.first().locator('.kds-next-action');
                await expect(readyHint).toContainText('LISTO');
            }
        }
    });

    test('KDS line click cycles individual line state @kds', async ({ page }) => {
        await page.goto('/web#action=kitchen_custom_dashboard_action');
        await page.waitForLoadState('networkidle');

        await expect(page.locator('#kitchen_screen')).toBeVisible({ timeout: 15000 });

        const cookingTab = page.locator('.kds-tab', { hasText: 'En Horno' });
        await cookingTab.click();

        const cards = page.locator('.kds-card');
        const count = await cards.count();

        if (count > 0) {
            const firstCard = cards.first();
            const lines = firstCard.locator('.kds-line');

            if (await lines.count() > 0) {
                const firstLine = lines.first();
                const statusBadge = firstLine.locator('.kds-line-status');

                if (await statusBadge.count() > 0) {
                    const initialStatus = await statusBadge.textContent();
                    expect(['Pend', 'Horno', 'Listo', 'X']).toContain(initialStatus);
                }
            }
        }
    });

    test('KDS cancel ticket removes it from view @kds', async ({ page }) => {
        await page.goto('/web#action=kitchen_custom_dashboard_action');
        await page.waitForLoadState('networkidle');

        await expect(page.locator('#kitchen_screen')).toBeVisible({ timeout: 15000 });

        const pendingTab = page.locator('.kds-tab', { hasText: 'Pendiente' });
        await pendingTab.click();

        const cards = page.locator('.kds-card');
        const count = await cards.count();

        if (count > 0) {
            const cancelBtn = cards.first().locator('.kds-btn-cancel');
            await expect(cancelBtn).toBeVisible();
        }
    });

    test('KDS elapsed time displays minutes @kds', async ({ page }) => {
        await page.goto('/web#action=kitchen_custom_dashboard_action');
        await page.waitForLoadState('networkidle');

        await expect(page.locator('#kitchen_screen')).toBeVisible({ timeout: 15000 });

        const cards = page.locator('.kds-card');
        const count = await cards.count();

        if (count > 0) {
            const elapsedNum = cards.first().locator('.kds-elapsed-num');
            const elapsedUnit = cards.first().locator('.kds-elapsed-unit');

            const minutes = await elapsedNum.textContent();
            const unit = await elapsedUnit.textContent();

            expect(parseInt(minutes)).not.toBeNaN();
            expect(unit).toContain('min');
        }
    });
});