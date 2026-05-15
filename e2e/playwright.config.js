import { defineConfig } from '@playwright/test';

export default defineConfig({
    testDir: './specs',
    timeout: 60000,
    expect: { timeout: 10000 },
    fullyParallel: false,
    retries: 1,
    workers: 1,
    reporter: [['list'], ['html', { open: 'never' }]],
    use: {
        baseURL: process.env.ODOO_URL || 'http://localhost:80',
        actionTimeout: 10000,
        navigationTimeout: 30000,
        screenshot: 'only-on-failure',
        video: 'retry-with-video',
        trace: 'on-first-retry',
    },
    projects: [
        {
            name: 'desktop-chrome',
            use: {
                browserName: 'chromium',
                viewport: { width: 1920, height: 1080 },
            },
        },
        {
            name: 'tablet-landscape',
            use: {
                browserName: 'chromium',
                viewport: { width: 1280, height: 800 },
                isMobile: true,
                hasTouch: true,
            },
        },
    ],
});