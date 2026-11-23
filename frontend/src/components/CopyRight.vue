<script setup lang="ts">
/** Also Apps 统一页脚：关于 / 联系 / 隐私 / 服务条款 / 版权。 */
const year = new Date().getFullYear()
</script>

<template>
  <footer class="footer">
    <div class="mx-auto max-w-6xl px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
      <div class="flex flex-wrap items-center justify-center gap-4 text-[12px]">
        <a href="https://www.alsoapp.com/" target="_blank" rel="noopener noreferrer" class="text-ink-3 hover:text-brand">关于 Also</a>
        <a href="mailto:contact@alsoapp.com" class="text-ink-3 hover:text-brand">联系我们</a>
        <a href="https://www.alsoapp.com/privacy/" target="_blank" rel="noopener noreferrer" class="text-ink-3 hover:text-brand">隐私政策</a>
        <a href="https://www.alsoapp.com/terms/" target="_blank" rel="noopener noreferrer" class="text-ink-3 hover:text-brand">服务条款</a>
      </div>
      <div class="text-[12px] text-ink-3">© {{ year }} Also Apps · All rights reserved.</div>
    </div>
  </footer>
</template>

<style scoped>
.footer {
  margin-top: auto;
  padding: 24px 0;
  border-top: 1px solid var(--color-line);
  background: var(--color-surface);
}
</style>
