<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <header class="topbar">
    <div class="brand"><RouterLink to="/">tools</RouterLink></div>
  </header>
  <div class="app">
    <t-result status="404" title="页面不存在" description="没有找到这个工具的路由。请确认地址，或返回工具集首页。">
      <template #extra>
        <RouterLink to="/"><t-button theme="primary">返回工具集</t-button></RouterLink>
      </template>
    </t-result>
  </div>
</template>
