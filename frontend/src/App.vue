<template>
  <RouterView v-if="route.path === '/login'" />
  <MainLayout v-else><RouterView /></MainLayout>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import MainLayout from './layouts/MainLayout.vue'
const route = useRoute()
</script>
