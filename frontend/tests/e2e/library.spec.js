const { expect, test } = require('@playwright/test')

const readyBook = { book_id: 'ready-book', title: 'A Small Garden', author: 'A. Reader', file_format: 'txt', total_words: 18000, ingest_status: 'ready', question_count: 2 }

test.beforeEach(async ({ page }) => {
  let books = [readyBook]
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/books')) return route.fulfill({ json: { books } })
    if (path.endsWith('/upload')) {
      expect(route.request().postData()).toContain('name="user_consent"')
      expect(route.request().postData()).toContain('true')
      books = [...books, { book_id: 'new-book', title: 'new-book.txt', ingest_status: 'uploaded', file_format: 'txt' }]
      return route.fulfill({ json: { book_id: 'new-book' } })
    }
    if (path.endsWith('/ingest/start')) { books = books.map(book => book.book_id === 'new-book' ? { ...book, ingest_status: 'parsing' } : book); return route.fulfill({ json: { status: 'started' } }) }
    if (path.endsWith('/query')) return route.fulfill({ json: { answer: 'Healthy soil helps roots retain water.', sources: ['passage-1'], source_details: [{ chunk_id: 'passage-1', chapter: 2, start_loc: 'word_34', excerpt: 'Healthy soil helps the roots develop and retain water.' }], confidence: .9 } })
    if (path.endsWith('/delete_book')) { books = []; return route.fulfill({ json: { success: true } }) }
    return route.fulfill({ status: 404, json: { detail: 'Not found' } })
  })
})

test('library search and filters recover from no matches', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'A Small Garden', level: 3 })).toBeVisible()
  const search = page.getByRole('searchbox', { name: 'Search your books' })
  await search.fill('no such book')
  await expect(page.getByText('A little more room to look.')).toBeVisible()
  await page.getByRole('button', { name: 'Clear search & filters' }).click()
  await expect(search).toHaveValue('')
  await expect(page.getByRole('button', { name: 'Open conversation' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
})

test('upload requires consent and then opens the processing library', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Add a book', exact: true }).first().click()
  await page.getByLabel('Choose a book file').setInputFiles({ name: 'new-book.txt', mimeType: 'text/plain', buffer: Buffer.from('Chapter 1\nA short book about plants.') })
  const submit = page.getByRole('button', { name: 'Add to my library' })
  await expect(submit).toBeDisabled()
  await page.getByRole('checkbox').check()
  await submit.click()
  await expect(page.getByRole('heading', { name: 'new-book.txt', level: 3 })).toBeVisible()
  await expect(page.getByText('Reading your book', { exact: true })).toBeVisible()
})

test('conversation shows verifiable source passages', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Open conversation' }).click()
  await page.getByLabel('Ask a question about this book').fill('What helps roots develop?')
  await page.getByRole('button', { name: 'Send question' }).click()
  await expect(page.getByText('Healthy soil helps roots retain water.', { exact: true })).toBeVisible()
  await page.getByText('Chapter 2', { exact: false }).click()
  await expect(page.getByText('Healthy soil helps the roots develop and retain water.', { exact: true })).toBeVisible()
})

test('deleting a book requires an explicit confirmation', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Delete A Small Garden' }).click()
  await page.getByRole('button', { name: 'Keep book' }).click()
  await expect(page.getByRole('heading', { name: 'A Small Garden', level: 3 })).toBeVisible()
  await page.getByRole('button', { name: 'Delete A Small Garden' }).click()
  await page.getByRole('button', { name: 'Delete book', exact: true }).click()
  await expect(page.getByText('Your next chapter starts here.')).toBeVisible()
})

test('failed queries can be retried without duplicating the question', async ({ page }) => {
  let failed = true
  await page.route('**/api/v1/query', route => failed ? route.fulfill({ status: 503, json: { detail: 'Please retry shortly.' } }) : route.fulfill({ json: { answer: 'A supported reply', sources: [], source_details: [] } }))
  await page.goto('/')
  await page.getByRole('button', { name: 'Open conversation' }).click()
  await page.getByLabel('Ask a question about this book').fill('A question to retry')
  await page.getByRole('button', { name: 'Send question' }).click()
  await expect(page.getByRole('alert', { name: 'Question failed' })).toContainText('Please retry shortly.')
  failed = false
  await page.getByRole('button', { name: 'Retry this question' }).click()
  await expect(page.getByText('A supported reply')).toBeVisible()
  await expect(page.getByText('A question to retry', { exact: true })).toHaveCount(1)
})
