<script lang="ts">
  interface Props {
    text: string;
    query: string;
  }

  let { text, query }: Props = $props();

  let terms = $derived.by(() => {
    if (!query.trim()) return [];
    return query
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, ' ')
      .split(/\s+/)
      .filter((t) => t.length > 2);
  });

  let parts = $derived.by(() => {
    if (terms.length === 0) return [{ text, isMatch: false }];
    const escapedTerms = terms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
    const regex = new RegExp(`(${escapedTerms})`, 'gi');
    const splitParts = text.split(regex);
    return splitParts.map((part) => ({
      text: part,
      isMatch: terms.some((t) => t.toLowerCase() === part.toLowerCase()),
    }));
  });
</script>

<span>
  {#each parts as part, i (i)}
    {#if part.isMatch}
      <mark class="bg-amber-100 dark:bg-amber-900/60 text-amber-950 dark:text-amber-200 font-medium px-0.5 rounded-xs">
        {part.text}
      </mark>
    {:else}
      <span>{part.text}</span>
    {/if}
  {/each}
</span>
