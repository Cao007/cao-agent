<template>
  <section class="extraction-result">
    <h2>{{ result.title }}</h2>
    <h3>摘要</h3><p>{{ result.summary }}</p>
    <h3>关键要点</h3><ul><li v-for="point in result.key_points" :key="point">{{ point }}</li></ul>
    <p v-if="!result.key_points.length">原文未提供</p>
    <h3>行动项</h3><ul><li v-for="item in result.action_items" :key="item">{{ item }}</li></ul>
    <p v-if="!result.action_items.length">原文未提供</p>
  </section>
</template>

<script setup lang="ts">
import type { Extraction } from '../../api/client'
defineProps<{ result: Extraction }>()
</script>
