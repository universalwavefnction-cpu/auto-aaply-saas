export const DEMO_STATS = {
  total_applications: 147,
  success_rate: 73,
  responses: 12,
}

export const DEMO_PLATFORM_DATA: [string, number][] = [
  ['stepstone', 89],
  ['linkedin', 34],
  ['xing', 24],
]

export const DEMO_STATUS_DATA: [string, number][] = [
  ['success', 108],
  ['pending', 23],
  ['failed', 11],
  ['skipped', 5],
]

export const DEMO_AUDIT_LOG = [
  {
    id: 1,
    time: '14:32:07',
    status: 'success' as const,
    title: 'Frontend Developer',
    company: 'SAP SE',
    platform: 'stepstone',
  },
  {
    id: 2,
    time: '14:31:44',
    status: 'success' as const,
    title: 'React Engineer',
    company: 'Zalando SE',
    platform: 'linkedin',
  },
  {
    id: 3,
    time: '14:30:18',
    status: 'pending' as const,
    title: 'Full Stack Developer',
    company: 'Deutsche Bank AG',
    platform: 'stepstone',
  },
  {
    id: 4,
    time: '14:28:55',
    status: 'success' as const,
    title: 'Software Engineer',
    company: 'Siemens AG',
    platform: 'xing',
  },
  {
    id: 5,
    time: '14:27:12',
    status: 'failed' as const,
    title: 'Backend Developer',
    company: 'BMW Group',
    platform: 'stepstone',
  },
  {
    id: 6,
    time: '14:25:30',
    status: 'success' as const,
    title: 'TypeScript Developer',
    company: 'Delivery Hero',
    platform: 'linkedin',
  },
]

export const DEMO_BOT_LOGS = [
  { level: 'info', event: 'start', message: 'Bot initialized — scanning StepStone...' },
  { level: 'info', event: 'search', message: 'Searching: "Frontend Engineer" in Berlin' },
  { level: 'info', event: 'found', message: 'Found 23 matching jobs on page 1' },
  { level: 'info', event: 'open', message: 'Opening: Frontend Developer at SAP SE' },
  { level: 'info', event: 'field_filled', message: 'Filling field: First Name → Max' },
  { level: 'info', event: 'field_filled', message: 'Filling field: Last Name → Mustermann' },
  { level: 'info', event: 'field_filled', message: 'Filling field: Email → m.mustermann@email.de' },
  { level: 'info', event: 'field_filled', message: 'Filling field: Phone → +49 171 234 5678' },
  { level: 'info', event: 'field_filled', message: 'Filling field: City → Berlin' },
  { level: 'info', event: 'upload', message: 'Uploading CV: resume_max_mustermann.pdf' },
  { level: 'info', event: 'field_filled', message: 'Generating cover letter with AI...' },
  { level: 'info', event: 'field_filled', message: 'Filling field: Salary Expectation → 65,000 €' },
  { level: 'info', event: 'clicking_apply', message: 'Clicking submit button...' },
  { level: 'info', event: 'submitting', message: 'Submitting application...' },
  { level: 'info', event: 'success', message: 'SUCCESS — Application submitted to SAP SE' },
  { level: 'info', event: 'open', message: 'Opening: React Engineer at Zalando SE' },
  { level: 'info', event: 'field_filled', message: 'Filling field: First Name → Max' },
  { level: 'info', event: 'field_filled', message: 'Filling field: Availability → Immediately' },
  { level: 'info', event: 'upload', message: 'Uploading CV: resume_max_mustermann.pdf' },
  { level: 'info', event: 'clicking_apply', message: 'Clicking submit button...' },
  { level: 'info', event: 'success', message: 'SUCCESS — Application submitted to Zalando SE' },
]

export const DEMO_APPLICATIONS = [
  { id: 1, title: 'Frontend Developer', company: 'SAP SE', platform: 'stepstone', status: 'success', date: '2026-03-02' },
  { id: 2, title: 'React Engineer', company: 'Zalando SE', platform: 'linkedin', status: 'success', date: '2026-03-02' },
  { id: 3, title: 'Full Stack Developer', company: 'Deutsche Bank AG', platform: 'stepstone', status: 'pending', date: '2026-03-02' },
  { id: 4, title: 'Software Engineer', company: 'Siemens AG', platform: 'xing', status: 'success', date: '2026-03-01' },
  { id: 5, title: 'Backend Developer', company: 'BMW Group', platform: 'stepstone', status: 'failed', date: '2026-03-01' },
  { id: 6, title: 'TypeScript Developer', company: 'Delivery Hero', platform: 'linkedin', status: 'success', date: '2026-03-01' },
  { id: 7, title: 'Senior Frontend Engineer', company: 'Bosch', platform: 'xing', status: 'success', date: '2026-02-28' },
  { id: 8, title: 'Web Developer', company: 'Allianz SE', platform: 'stepstone', status: 'pending', date: '2026-02-28' },
]

export const DEMO_PROFILE = {
  first_name: 'Max',
  last_name: 'Mustermann',
  phone: '+49 171 234 5678',
  city: 'Berlin',
  zip_code: '10115',
  email: 'm.mustermann@email.de',
  salary: '65,000',
  experience: '4',
  summary: 'Experienced frontend developer with 4+ years building React applications. Passionate about clean UI, TypeScript, and performance optimization.',
}

export const DEMO_QA_PAIRS = [
  { q: 'Earliest start date?', a: 'Immediately' },
  { q: 'Do you have a work permit for Germany?', a: 'Yes' },
  { q: 'Salary expectation?', a: '60,000 – 70,000 € per year' },
]

export const DEMO_CREDENTIALS = [
  { platform: 'StepStone', email: 'm.mustermann@email.de', connected: true },
  { platform: 'LinkedIn', email: 'm.mustermann@email.de', connected: true },
]

export const TOUR_STEPS = [
  {
    title: 'Mission Control',
    subtitle: 'Your command center',
    description: 'Real-time stats for all your applications. Launch the bot with one click — pick a job title, location, and platform.',
  },
  {
    title: 'Your Profile',
    subtitle: 'The bot\'s brain',
    description: 'Upload your CV, add credentials, and answer common questions. The bot uses this to fill every application form automatically.',
  },
  {
    title: 'Live Bot',
    subtitle: 'Watch it work',
    description: 'See every field filled, every form submitted in real-time. The bot navigates job platforms just like you would — but 100x faster.',
  },
  {
    title: 'Applications',
    subtitle: 'Track everything',
    description: 'Every application is logged with status, platform, and timestamp. Know exactly where you applied and what happened.',
  },
  {
    title: 'Ready?',
    subtitle: 'Start automating',
    description: '',
  },
]
