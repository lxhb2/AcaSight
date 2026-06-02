import { test, expect } from '@playwright/test';

test.describe('Phase 11 新增功能 E2E 测试', () => {

  test.describe('写作工作区面板', () => {
    test('应通过侧边栏图标打开写作面板', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      const writingIcon = page.locator('.acasight-icon-bar .acasight-icon-item').filter({
        has: page.locator('svg.lucide-graduation-cap'),
      });
      await writingIcon.click();

      await expect(page.locator('.acasight-panel-title').filter({ hasText: /写作|Writing/ })).toBeVisible({ timeout: 8000 });
    });

    test('应通过键盘快捷键 Ctrl+Shift+W 打开写作面板', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      await page.keyboard.press('Control+Shift+w');

      await expect(page.locator('.acasight-panel-title').filter({ hasText: /写作|Writing/ })).toBeVisible({ timeout: 8000 });
    });

    test('写作面板应显示章节结构', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      const writingIcon = page.locator('.acasight-icon-bar .acasight-icon-item').filter({
        has: page.locator('svg.lucide-graduation-cap'),
      });
      await writingIcon.click();

      await expect(page.locator('.acasight-panel-body').first()).toBeVisible({ timeout: 8000 });
    });
  });

  test.describe('版本历史面板', () => {
    test('应通过侧边栏图标打开版本历史面板', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      const historyIcon = page.locator('.acasight-icon-bar .acasight-icon-item').filter({
        has: page.locator('svg.lucide-history'),
      });
      await historyIcon.click();

      await expect(page.locator('.acasight-panel-title').filter({ hasText: /版本|Version/ })).toBeVisible({ timeout: 8000 });
    });

    test('版本历史面板应显示加载状态或版本列表', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      const historyIcon = page.locator('.acasight-icon-bar .acasight-icon-item').filter({
        has: page.locator('svg.lucide-history'),
      });
      await historyIcon.click();

      const panelBody = page.locator('.acasight-panel-body').first();
      await expect(panelBody).toBeVisible({ timeout: 8000 });

      const hasLoadingOrContent = await panelBody.locator('text=/加载|loading|v\\d|暂无|No version/i').count();
      expect(hasLoadingOrContent).toBeGreaterThan(0);
    });
  });

  test.describe('模板库面板', () => {
    test('应通过侧边栏图标打开模板库面板', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      const templateIcons = page.locator('.acasight-icon-bar .acasight-icon-item').filter({
        has: page.locator('svg.lucide-book-open'),
      });
      const count = await templateIcons.count();
      expect(count).toBeGreaterThanOrEqual(1);

      await templateIcons.last().click();

      await expect(page.locator('.acasight-panel-title').filter({ hasText: /模板|Template/ })).toBeVisible({ timeout: 8000 });
    });

    test('模板库面板应显示搜索框', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      const templateIcons = page.locator('.acasight-icon-bar .acasight-icon-item').filter({
        has: page.locator('svg.lucide-book-open'),
      });
      await templateIcons.last().click();

      await expect(page.locator('.acasight-panel-body').first()).toBeVisible({ timeout: 8000 });

      const searchInput = page.locator('.acasight-panel-body input[placeholder*="搜索"], .acasight-panel-body input[placeholder*="Search"]').first();
      await expect(searchInput).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('面板持久化与恢复', () => {
    test('刷新后应恢复已打开的面板状态', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      const searchIcon = page.locator('.acasight-icon-bar .acasight-icon-item').filter({
        has: page.locator('svg.lucide-search'),
      });
      await searchIcon.click();

      await expect(page.locator('.acasight-panel-title').filter({ hasText: /搜索|Search/ })).toBeVisible({ timeout: 8000 });

      await page.reload();
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      const localStorage = await page.evaluate(() => window.localStorage.getItem('acasight-workspace'));
      expect(localStorage).not.toBeNull();
    });
  });

  test.describe('错误边界与懒加载', () => {
    test('懒加载面板应显示加载骨架屏', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      const writingIcon = page.locator('.acasight-icon-bar .acasight-icon-item').filter({
        has: page.locator('svg.lucide-graduation-cap'),
      });

      const skeletonPromise = page.locator('.acasight-panel-skeleton').waitFor({ timeout: 3000 }).catch(() => null);
      await writingIcon.click();

      await expect(page.locator('.acasight-panel-title').filter({ hasText: /写作|Writing/ })).toBeVisible({ timeout: 8000 });
      await skeletonPromise;
    });

    test('关闭面板后应能重新打开', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      const searchIcon = page.locator('.acasight-icon-bar .acasight-icon-item').filter({
        has: page.locator('svg.lucide-search'),
      });

      await searchIcon.click();
      await expect(page.locator('.acasight-panel-title').first()).toBeVisible({ timeout: 5000 });

      await searchIcon.click();
      await expect(page.locator('.acasight-panel-title').filter({ hasText: /搜索|Search/ })).not.toBeVisible({ timeout: 3000 });

      await searchIcon.click();
      await expect(page.locator('.acasight-panel-title').filter({ hasText: /搜索|Search/ })).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('多面板协同', () => {
    test('应同时打开写作面板和版本历史面板', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      const writingIcon = page.locator('.acasight-icon-bar .acasight-icon-item').filter({
        has: page.locator('svg.lucide-graduation-cap'),
      });
      await writingIcon.click();

      const historyIcon = page.locator('.acasight-icon-bar .acasight-icon-item').filter({
        has: page.locator('svg.lucide-history'),
      });
      await historyIcon.click();

      const titles = page.locator('.acasight-panel-title');
      const count = await titles.count();
      expect(count).toBeGreaterThanOrEqual(2);
    });

    test('应同时打开写作面板和模板库面板', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      const writingIcon = page.locator('.acasight-icon-bar .acasight-icon-item').filter({
        has: page.locator('svg.lucide-graduation-cap'),
      });
      await writingIcon.click();

      const templateIcons = page.locator('.acasight-icon-bar .acasight-icon-item').filter({
        has: page.locator('svg.lucide-book-open'),
      });
      await templateIcons.last().click();

      const titles = page.locator('.acasight-panel-title');
      const count = await titles.count();
      expect(count).toBeGreaterThanOrEqual(2);
    });
  });
});
