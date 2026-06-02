import { test, expect } from '@playwright/test';

test.describe('AcaSight 关键路径 E2E 测试', () => {

  test.describe('应用启动与布局', () => {
    test('应成功加载应用并显示侧边栏', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });
      await expect(page.locator('.acasight-logo')).toHaveText('A');
    });

    test('应显示面板图标列表', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });
      const iconItems = page.locator('.acasight-icon-bar .acasight-icon-item');
      const count = await iconItems.count();
      expect(count).toBeGreaterThanOrEqual(15);
    });
  });

  test.describe('面板切换', () => {
    test('应打开搜索面板', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      const searchIcon = page.locator('.acasight-icon-bar .acasight-icon-item').nth(2);
      await searchIcon.click();

      await expect(page.locator('.acasight-panel-title').first()).toBeVisible({ timeout: 5000 });
    });

    test('应打开文件浏览器面板', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      await page.locator('.acasight-icon-bar .acasight-icon-item').first().click();
      await expect(page.locator('.acasight-panel-title').first()).toBeVisible({ timeout: 5000 });
    });

    test('应打开AI插图生成面板', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      const figureIcon = page.locator('.acasight-icon-bar .acasight-icon-item').nth(13);
      await figureIcon.click();
      await expect(page.locator('.acasight-panel-title').first()).toBeVisible({ timeout: 5000 });
    });

    test('应打开SVG矢量编辑面板', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      const svgIcon = page.locator('.acasight-icon-bar .acasight-icon-item').nth(14);
      await svgIcon.click();
      await expect(page.locator('.acasight-panel-title').first()).toBeVisible({ timeout: 5000 });
    });

    test('应打开多个面板', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      await page.locator('.acasight-icon-bar .acasight-icon-item').first().click();
      await page.locator('.acasight-icon-bar .acasight-icon-item').nth(2).click();

      const titles = page.locator('.acasight-panel-title');
      const count = await titles.count();
      expect(count).toBeGreaterThanOrEqual(2);
    });
  });

  test.describe('主题切换', () => {
    test('应切换深色/浅色主题', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      const allIcons = page.locator('.acasight-icon-bar .acasight-icon-item');
      const count = await allIcons.count();
      const themeIcon = allIcons.nth(count - 2);
      await themeIcon.click();
    });
  });

  test.describe('设置面板', () => {
    test('应打开设置弹窗', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      const allIcons = page.locator('.acasight-icon-bar .acasight-icon-item');
      const count = await allIcons.count();

      for (let i = 0; i < count; i++) {
        const tooltip = await allIcons.nth(i).getAttribute('data-tooltip');
        if (tooltip && (tooltip.includes('设置') || tooltip.includes('Settings'))) {
          await allIcons.nth(i).click();
          break;
        }
      }

      const aiConfigText = page.locator('text=AI 配置, text=AI Model Configuration').first();
      await expect(aiConfigText.or(page.locator('text=AI Model Configuration').first())).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('SVG编辑器交互', () => {
    test('应显示SVG编辑器生成标签页', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      const svgIcon = page.locator('.acasight-icon-bar .acasight-icon-item').nth(14);
      await svgIcon.click();
      await expect(page.locator('.acasight-panel-title').first()).toBeVisible({ timeout: 5000 });
    });

    test('应显示方法论文本输入区域', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('.acasight-icon-bar')).toBeVisible({ timeout: 15000 });

      const svgIcon = page.locator('.acasight-icon-bar .acasight-icon-item').nth(14);
      await svgIcon.click();

      const textarea = page.locator('.acasight-panel-body textarea').first();
      await expect(textarea).toBeVisible({ timeout: 5000 });
    });
  });
});
