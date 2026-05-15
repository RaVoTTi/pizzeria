import { test, expect } from '@playwright/test';
import { odooLogin, ODOO } from '../helpers/odoo';

test.describe('Backend: Kitchen Ticket Model (via browser RPC)', () => {

    let authenticatedCookie;

    test.beforeAll(async ({ browser }) => {
        const context = await browser.newContext();
        const page = await context.newPage();
        await odooLogin(page);
        const cookies = await context.cookies();
        authenticatedCookie = cookies;
        await context.close();
    });

    async function jsonRpcViaBrowser(page, model, method, args = [], kwargs = {}) {
        return await page.evaluate(async ({ db, model, method, args, kwargs }) => {
            const sessionToken = document.querySelector('input[name="csrf_token"]')?.value
                || document.querySelector('[name="csrf_token"]')?.value;
            const rpc = window.__odoo ? undefined : undefined;

            const response = await fetch('/jsonrpc', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        service: 'object',
                        method: 'execute_kw',
                        args: [db, 2, '9vyf-dcwb-bmp6', model, method, args, kwargs],
                    },
                    id: Date.now(),
                }),
            });
            const json = await response.json();
            if (json.error) {
                throw new Error(`JSON-RPC error: ${JSON.stringify(json.error)}`);
            }
            return json.result;
        }, { db: ODOO.DB, model, method, args, kwargs });
    }

    test('pos.kitchen.ticket model is accessible @kds', async ({ page }) => {
        await odooLogin(page);
        const fields = await jsonRpcViaBrowser(page, 'pos.kitchen.ticket', 'fields_get', [], {
            attributes: ['string', 'type', 'required'],
        });
        expect(fields).toHaveProperty('origin_pos_order_id');
        expect(fields).toHaveProperty('state');
        expect(fields).toHaveProperty('ticket_type');
        expect(fields).toHaveProperty('payment_status');
        expect(fields).toHaveProperty('line_ids');
    });

    test('pos.kitchen.ticket.line model is accessible @kds', async ({ page }) => {
        await odooLogin(page);
        const fields = await jsonRpcViaBrowser(page, 'pos.kitchen.ticket.line', 'fields_get', [], {
            attributes: ['string', 'type'],
        });
        expect(fields).toHaveProperty('ticket_id');
        expect(fields).toHaveProperty('product_id');
        expect(fields).toHaveProperty('full_product_name');
        expect(fields).toHaveProperty('state');
        expect(fields).toHaveProperty('qty_total');
    });

    test('get_details returns an array @kds', async ({ page }) => {
        await odooLogin(page);
        const configIds = await jsonRpcViaBrowser(page, 'pos.config', 'search', [[]]);
        if (configIds.length === 0) return;

        const details = await jsonRpcViaBrowser(page, 'pos.kitchen.ticket', 'get_details', [configIds[0]]);
        expect(Array.isArray(details)).toBe(true);
    });

    test('kitchen.screen model exists with printer_name field @kds', async ({ page }) => {
        await odooLogin(page);
        const fields = await jsonRpcViaBrowser(page, 'kitchen.screen', 'fields_get', [], {
            attributes: ['string', 'type'],
        });
        expect(fields).toHaveProperty('pos_config_id');
        expect(fields).toHaveProperty('pos_categ_ids');
        expect(fields).toHaveProperty('printer_name');
    });
});