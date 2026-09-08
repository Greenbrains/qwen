# Навык: Маркетинг (Marketing Agent)

## Описание
Специализированный навык для маркетинговых задач: анализ конкурентов, копирайтинг, SEO, создание презентаций PPTX.
Использует инструменты веб-поиска, выполнения кода и работы с файлами.

## Когда использовать
- «Проанализируй конкурентов»
- «Напиши текст для лендинга»
- «Создай презентацию продукта»
- «Подбери ключевые слова для SEO»

## Под-навыки

### 1. product-marketing-context
Создание документа контекста продукта (ICP, позиционирование, ЦА).
Запусти в начале проекта — на него ссылаются остальные под-навыки.

### 2. competitive-landscape
Анализ конкурентов: прямые/вторичные/косвенные, таблица в XLSX.
Используй `web_search` для сбора данных, `execute_code` для выгрузки в таблицу.

### 3. copywriting
Написание маркетинговых текстов: заголовки, лендинг, email, объявления.
Опирайся на язык клиентов из контекста продукта.

### 4. seo
SEO-оптимизация: семантические кластеры, контент-план, мета-теги.
Используй `web_search` для расширения запросов.

### 5. presentation
Генерация презентаций PPTX через `execute_code` с библиотекой `python-pptx`.

## Рабочий процесс

### Шаг 1: Определение задачи
Уточни, какой под-навык нужен пользователю. Если неясно — спроси.

### Шаг 2: Сбор информации
- Проверь наличие `.agents/product-marketing-context.md`.
- При необходимости используй `web_search` для свежих данных.

### Шаг 3: Выполнение задачи
Следуй инструкциям конкретного под-навыка (см. ниже).

### Шаг 4: Выгрузка результата
Используй `execute_code` для создания файлов (XLSX, PPTX, DOCX, MD).

---

## Под-навык: presentation (генерация презентаций PPTX)

**Когда:** «сделай презентацию», «PPTX», «слайды», «pitch deck».

### Рецепт кода для `execute_code`:
```python
try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "-q", "python-pptx"])
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Титульный слайд
slide = prs.slides.add_slide(prs.slide_layouts[6])
txBox = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(11), Inches(2))
tf = txBox.text_frame
tf.text = "Заголовок презентации"
tf.paragraphs[0].font.size = Pt(54)
tf.paragraphs[0].font.bold = True
tf.paragraphs[0].alignment = PP_ALIGN.CENTER

# Контентные слайды
for title, bullets in slides_content:
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = title
    body = slide.placeholders[1].text_frame
    body.clear()
    for bullet in bullets:
        p = body.add_paragraph()
        p.text = bullet
        p.level = 0
        p.font.size = Pt(24)

prs.save("presentation.pptx")
print("presentation.pptx")
```

**Важно:** Не хардкодь путь `output/` — `execute_code` сам скачает артефакт.

---

## Ограничения и качество
- Не выдумывай цифры и факты — всегда прикладывай URL-источники.
- Разделяй факты из источников и свои выводы.
- Для кириллицы в PPTX/DOCX проблемы нет (Unicode работает).
