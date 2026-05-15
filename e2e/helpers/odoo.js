export const ODOO = {
    URL: process.env.ODOO_URL || 'http://localhost:80',
    DB: process.env.ODOO_DB || 'elgordo',
    USER: process.env.ODOO_USER || 'admin',
    PASS: process.env.ODOO_PASS || '9vyf-dcwb-bmp6',
};

export async function odooLogin(page) {
    await page.goto('/web/login');
    await page.waitForLoadState('networkidle');

    const loginField = page.locator('#login');
    const passField = page.locator('#password');

    await loginField.fill(ODOO.USER);
    await passField.fill(ODOO.PASS);

    await page.click('button[type="submit"]');

    await page.waitForURL(/\/web/, { timeout: 20000 });
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
}