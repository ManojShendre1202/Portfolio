// ── file helpers ──
export function getFileEmoji(name) {
  const ext = name.split('.').pop().toLowerCase()
  if (['jpg','jpeg','png','webp','tiff','bmp'].includes(ext)) return '🖼️'
  if (ext === 'pdf')  return '📄'
  if (['docx','doc'].includes(ext)) return '📝'
  if (['xlsx','xls','csv'].includes(ext)) return '📊'
  if (ext === 'dxf')  return '📐'
  if (ext === 'txt')  return '📃'
  return '📎'
}

export function getDocType(file) {
  if (file._sample) return file._sample.docType
  const ext = file.name.split('.').pop().toLowerCase()
  if (['jpg','jpeg','png','webp'].includes(ext)) return 'Natural Image'
  if (ext === 'pdf')  return 'PDF Document'
  if (['docx','doc'].includes(ext)) return 'Word Document'
  if (['xlsx','xls','csv'].includes(ext)) return 'Spreadsheet'
  if (ext === 'dxf')  return 'Engineering Drawing'
  if (ext === 'txt')  return 'Text File'
  return 'Document'
}

export function fmtSize(bytes) {
  if (bytes > 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  return Math.round(bytes / 1024) + ' KB'
}

// ── action suggestions by doc type ──
export function getActions(docType) {
  if (docType.includes('Resume')) return [
    { emoji: '🎯', label: 'Skill gap analysis' },
    { emoji: '📧', label: 'Draft email' },
    { emoji: '⚡', label: 'Roast this' },
    { emoji: '🔗', label: 'LinkedIn search' },
  ]
  if (docType.includes('Research')) return [
    { emoji: '✨', label: 'Summarize' },
    { emoji: '🧠', label: 'ELI10' },
    { emoji: '📚', label: 'Related papers' },
    { emoji: '✅', label: 'Fact-check' },
  ]
  if (docType.includes('Image')) return [
    { emoji: '👁️', label: 'Describe image' },
    { emoji: '📝', label: 'Extract text' },
    { emoji: '🌍', label: 'Translate' },
    { emoji: '🕵️', label: 'What secrets?' },
  ]
  if (docType.includes('Spreadsheet')) return [
    { emoji: '📊', label: 'Visualize data' },
    { emoji: '✨', label: 'Summarize' },
    { emoji: '🔍', label: 'Find anomalies' },
  ]
  if (docType.includes('Engineering')) return [
    { emoji: '📐', label: 'Extract BOM' },
    { emoji: '🔍', label: 'Analyze components' },
    { emoji: '✨', label: 'Summarize drawing' },
  ]
  return [
    { emoji: '✨', label: 'Summarize' },
    { emoji: '🤔', label: 'Explain simply' },
    { emoji: '🕵️', label: 'Key insights' },
  ]
}

// ── processing steps ──
export const PROC_STEPS = [
  { id: 'classify',  label: 'Classifying document' },
  { id: 'extract',   label: 'Extracting content' },
  { id: 'structure', label: 'Structuring data' },
  { id: 'index',     label: 'Building knowledge base' },
  { id: 'suggest',   label: 'Generating insights' },
]

export function getStepDetail(stepId, docType) {
  return {
    classify:  docType,
    extract:   docType.includes('Image') ? 'Gemini Vision' : 'PyMuPDF · direct',
    structure: 'Gemini 1.5 Flash',
    index:     Math.floor(Math.random() * 15 + 5) + ' chunks indexed',
    suggest:   'Actions ready',
  }[stepId]
}

// ── welcome messages ──
export function getWelcomeMessage(docType, fileName) {
  const map = {
    'Professional Resume': `I've analyzed this resume. Skills, experience, and education are all clearly extracted. What would you like to know — or try one of the actions above.`,
    'Research Paper':      `I've read through this paper and indexed the key findings, methodology, and conclusions. Ask me anything or try a suggested action.`,
    'Natural Image':       `I've processed this image using vision analysis. I can describe what's in it, extract any text, or answer questions about it.`,
    'Spreadsheet':         `Spreadsheet analyzed. I can answer questions about the data, find patterns, or help visualize it.`,
    'Engineering Drawing': `Drawing analyzed via ezdxf. I can extract components, BOM data, or answer structural questions.`,
  }
  return map[docType] || `I've processed "${fileName}" and it's ready for questions.`
}

// ── mock AI responses ──
export const MOCK_RESPONSES = {
  'Skill gap analysis': 'Based on the resume, the candidate is strong in Python, Computer Vision (OpenCV, YOLO), and Django. For a typical ML Engineer role, gaps include: distributed training (PyTorch DDP), MLOps tooling (MLflow, Kubeflow), and cloud ML services (Vertex AI, SageMaker). Recommendation: prioritize MLflow and Vertex AI next.',
  'Draft email': 'Subject: Exploring Opportunities — Manoj Shendre\n\nHi [Name],\n\nI came across your team\'s work and I\'m excited by the problems you\'re solving. With 2 years of production Computer Vision experience across Indian Railways, L&T, and Mahindra Aerospace, I believe I can contribute meaningfully.\n\nWould you be open to a 20-minute conversation?\n\nBest,\nManoj',
  'Roast this': '⚡ Alright, here\'s your roast:\n\nThe resume says "Production AI Systems" — but I notice the projects section is doing more heavy lifting than the experience section. Also, "familiar with Docker" is the resume equivalent of saying you\'ve seen a gym. We\'re rooting for you though. 💪',
  'Summarize': 'This document covers the core ideas, methodology, and key findings. The main thesis is clear and well-supported. Three key takeaways: (1) the problem is well-defined, (2) the approach is novel compared to existing work, (3) results show meaningful improvement over baselines.',
  'ELI10': 'Okay imagine you have a really complicated LEGO set with no instructions. This paper is basically someone figuring out the best way to sort all the LEGO pieces first so building goes 10x faster. That\'s it. Sorted pieces = faster building = better result.',
  'Describe image': 'The image shows visual content with structured information. I can see patterns, possible text, and compositional elements. For full vision analysis, the production version routes this through Gemini Vision for accurate understanding.',
  'Extract BOM': 'Bill of Materials extracted:\n- Component A: 4 instances\n- Component B: 12 instances\n- Connector type X: 8 instances\n- Assembly bracket: 2 instances\n\nTotal unique component types: 4\nTotal components: 26',
}

export function generateFallbackReply(question, docType) {
  const q = question.toLowerCase()
  if (q.includes('skill') || q.includes('experience')) return 'Based on the document content, I can see relevant skills and experience. The key strengths appear to be in technical implementation with production-level exposure. Want me to go deeper on any specific area?'
  if (q.includes('summar')) return 'Here\'s a concise summary: The document presents structured information across multiple sections. The core message is clear, well-organized, and backed by specific examples or data points.'
  if (q.includes('what') && q.includes('about')) return `This document is primarily about ${docType.toLowerCase()} content. It's structured to communicate specific information clearly and concisely.`
  return `Good question. Based on my analysis of this ${docType.toLowerCase()}, the content addresses this directly. The relevant section indicates strong alignment with what you\'re asking. Want me to be more specific?`
}

// ── samples ──
export const SAMPLES = {
  resume: { name: 'Manoj_Shendre_Resume.pdf',        size: 420000, _sample: { docType: 'Professional Resume' } },
  paper:  { name: 'Attention_Is_All_You_Need.pdf',   size: 1200000, _sample: { docType: 'Research Paper' } },
  image:  { name: 'random_image.png',                size: 850000, _sample: { docType: 'Natural Image' } },
}
