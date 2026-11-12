import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// 别名必须与 tsconfig.app.json 的 baseUrl+paths 保持一致，否则 @/ 导入会退化成 any
export default defineConfig({
  // GitHub Pages project site 部署在 /<repo>/ 下（本仓库名 tools），故 base=/tools/。
  // 允许用 VITE_PUBLIC_PATH 覆盖（换 repo 名 / 绑自定义域根路径时），默认 /tools/。
  // 所有静态资源 JS/CSS 会内联此前缀，保证 Pages 子路径下能正确加载。
  base: process.env.VITE_PUBLIC_PATH || '/tools/',
  // tailwindcss() 走 Vite 原生插件（Tailwind v4，无需 postcss.config / tailwind.config）
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    // 产物交给 FastAPI 托管；关闭 sourcemap 避免泄漏源码路径
    outDir: 'dist',
    sourcemap: false,
  },
})
