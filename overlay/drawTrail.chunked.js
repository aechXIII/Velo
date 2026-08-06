  // Chunked core pass (backup)
  ctx.shadowBlur = 0;
  ctx.lineWidth = width * 1.2;
  const CHUNK_SIZE = 12;
  for (let ci = 0; ci < path.length - 1; ci += CHUNK_SIZE - 1) {
    const end = Math.min(ci + CHUNK_SIZE, path.length);
    const chunk = path.slice(ci, end);
    ctx.strokeStyle = makePathGradient(chunk, 12, end >= path.length);
    strokePath(chunk);
  }
