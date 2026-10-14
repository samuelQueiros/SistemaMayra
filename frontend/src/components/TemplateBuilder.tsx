import { Plus, Trash2 } from 'lucide-react'
import type {
  AgeBracket,
  ClassificationRange,
  ComparisonOperator,
  FieldType,
  TemplateArea,
  TemplateField,
  TemplateSchemaJSON,
} from '../api/types'
import { Button, Card, IconButton, Input, Select } from './ds'

function slugify(texto: string): string {
  const limpo = texto
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
  return limpo || 'item'
}

const TIPOS_DE_CAMPO: { value: FieldType; label: string }[] = [
  { value: 'scale', label: 'Numérico (escala)' },
  { value: 'boolean', label: 'Sim / Não' },
  { value: 'select', label: 'Múltipla escolha' },
  { value: 'text', label: 'Texto livre' },
]

const COMPARACOES: { value: ComparisonOperator; label: string }[] = [
  { value: 'gte', label: '≥ (maior ou igual)' },
  { value: 'gt', label: '> (maior que)' },
  { value: 'lte', label: '≤ (menor ou igual)' },
  { value: 'lt', label: '< (menor que)' },
  { value: 'eq', label: '= (igual)' },
]

interface TemplateBuilderProps {
  value: TemplateSchemaJSON
  onChange: (next: TemplateSchemaJSON) => void
}

export default function TemplateBuilder({ value, onChange }: TemplateBuilderProps) {
  function atualizar(patch: Partial<TemplateSchemaJSON>) {
    onChange({ ...value, ...patch })
  }

  function mudarRuleType(rule_type: TemplateSchemaJSON['rule_type']) {
    // Trocar o tipo de regra muda o formato esperado das faixas de
    // classificação — mais seguro recomeçar essa parte do zero do que
    // manter faixas com campos que não fazem mais sentido.
    atualizar({ rule_type, classification_ranges: [] })
  }

  function adicionarArea() {
    const nova: TemplateArea = {
      key: slugify(`area_${value.areas.length + 1}`),
      label: `Área ${value.areas.length + 1}`,
      fields: value.rule_type === 'age_equivalent_percentage' ? undefined : [],
      age_brackets: value.rule_type === 'age_equivalent_percentage' ? [] : undefined,
    }
    atualizar({ areas: [...value.areas, nova] })
  }

  function atualizarArea(indice: number, area: TemplateArea) {
    const areas = [...value.areas]
    areas[indice] = area
    atualizar({ areas })
  }

  function removerArea(indice: number) {
    atualizar({ areas: value.areas.filter((_, i) => i !== indice) })
  }

  function adicionarFaixa() {
    const nova: ClassificationRange =
      value.rule_type === 'count_threshold'
        ? { label: 'Nova Faixa', area: value.areas[0]?.key ?? '', minimum_count: 1, comparison: 'gte' }
        : { label: 'Nova Faixa', min: 0, max: 10 }
    atualizar({ classification_ranges: [...value.classification_ranges, nova] })
  }

  function atualizarFaixa(indice: number, faixa: ClassificationRange) {
    const faixas = [...value.classification_ranges]
    faixas[indice] = faixa
    atualizar({ classification_ranges: faixas })
  }

  function removerFaixa(indice: number) {
    atualizar({ classification_ranges: value.classification_ranges.filter((_, i) => i !== indice) })
  }

  return (
    <div style={{ display: 'grid', gap: 'var(--s-5)' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 'var(--s-4)' }}>
        <Input
          label="Nome Da Escala"
          value={value.name}
          onChange={(e) => atualizar({ name: e.target.value })}
          required
        />
        <Select
          label="Tipo De Regra De Pontuação"
          value={value.rule_type}
          onChange={(e) => mudarRuleType(e.target.value as TemplateSchemaJSON['rule_type'])}
          options={[
            { value: 'sum_threshold', label: 'Soma pontos e compara com faixas (ex.: CARS, ATA)' },
            { value: 'count_threshold', label: 'Conta itens em um valor específico (ex.: SNAP-IV)' },
            { value: 'age_equivalent_percentage', label: 'Compara com idade cronológica (ex.: Portage)' },
          ]}
        />
        <Select
          label="Tipo De Gráfico"
          value={value.chart.type}
          onChange={(e) => atualizar({ chart: { ...value.chart, type: e.target.value as 'bar' | 'radar' | 'pie' } })}
          options={[
            { value: 'bar', label: 'Barras' },
            { value: 'radar', label: 'Radar' },
            { value: 'pie', label: 'Pizza' },
          ]}
        />
      </div>

      {value.rule_type === 'count_threshold' && (
        <Input
          label="Valores Que Contam (Separados Por Vírgula)"
          hint='Ex.: "bastante, demais" — respostas que entram na contagem de cada área.'
          value={(value.target_values ?? []).join(', ')}
          onChange={(e) =>
            atualizar({ target_values: e.target.value.split(',').map((v) => v.trim()).filter(Boolean) })
          }
        />
      )}

      {value.rule_type === 'age_equivalent_percentage' && (
        <ItemScoringEditor
          value={value.item_scoring ?? {}}
          onChange={(item_scoring) => atualizar({ item_scoring })}
        />
      )}

      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--s-3)' }}>
          <h3 style={{ font: 'var(--type-h3)', margin: 0 }}>Áreas</h3>
          <Button type="button" size="sm" variant="secondary" icon={<Plus size={14} />} onClick={adicionarArea}>
            Adicionar Área
          </Button>
        </div>
        <div style={{ display: 'grid', gap: 'var(--s-3)' }}>
          {value.areas.map((area, i) => (
            <AreaEditor
              key={i}
              ruleType={value.rule_type}
              area={area}
              onChange={(a) => atualizarArea(i, a)}
              onRemove={() => removerArea(i)}
            />
          ))}
          {value.areas.length === 0 && (
            <p style={{ color: 'var(--text-2)', font: 'var(--type-caption)' }}>Nenhuma área ainda.</p>
          )}
        </div>
      </div>

      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--s-3)' }}>
          <h3 style={{ font: 'var(--type-h3)', margin: 0 }}>Faixas De Classificação</h3>
          <Button type="button" size="sm" variant="secondary" icon={<Plus size={14} />} onClick={adicionarFaixa}>
            Adicionar Faixa
          </Button>
        </div>
        <div style={{ display: 'grid', gap: 'var(--s-3)' }}>
          {value.classification_ranges.map((faixa, i) => (
            <ClassificationRangeEditor
              key={i}
              ruleType={value.rule_type}
              areaKeys={value.areas.map((a) => a.key)}
              range={faixa}
              onChange={(f) => atualizarFaixa(i, f)}
              onRemove={() => removerFaixa(i)}
            />
          ))}
          {value.classification_ranges.length === 0 && (
            <p style={{ color: 'var(--text-2)', font: 'var(--type-caption)' }}>Nenhuma faixa ainda.</p>
          )}
        </div>
      </div>
    </div>
  )
}

function AreaEditor({
  ruleType,
  area,
  onChange,
  onRemove,
}: {
  ruleType: TemplateSchemaJSON['rule_type']
  area: TemplateArea
  onChange: (area: TemplateArea) => void
  onRemove: () => void
}) {
  function adicionarCampo() {
    const campos = area.fields ?? []
    const novo: TemplateField = { key: slugify(`campo_${campos.length + 1}`), label: `Campo ${campos.length + 1}`, type: 'scale', min: 0, max: 4, weight: 1 }
    onChange({ ...area, fields: [...campos, novo] })
  }

  function adicionarFaixaEtaria() {
    const faixas = area.age_brackets ?? []
    const nova: AgeBracket = { label: `Faixa ${faixas.length + 1}`, max_age_months: 24, fields: [] }
    onChange({ ...area, age_brackets: [...faixas, nova] })
  }

  return (
    <Card tone="sunken" style={{ boxShadow: 'none' }}>
      <div style={{ display: 'grid', gap: 'var(--s-3)' }}>
        <div style={{ display: 'flex', gap: 'var(--s-3)', alignItems: 'flex-end' }}>
          <Input label="Nome Da Área" value={area.label} onChange={(e) => onChange({ ...area, label: e.target.value })} style={{ flex: 1 }} />
          <IconButton label="Remover área" icon={<Trash2 size={16} />} variant="secondary" onClick={onRemove} />
        </div>

        {ruleType !== 'age_equivalent_percentage' ? (
          <div style={{ display: 'grid', gap: 'var(--s-2)' }}>
            {(area.fields ?? []).map((campo, i) => (
              <FieldEditor
                key={i}
                field={campo}
                onChange={(f) => {
                  const campos = [...(area.fields ?? [])]
                  campos[i] = f
                  onChange({ ...area, fields: campos })
                }}
                onRemove={() => onChange({ ...area, fields: (area.fields ?? []).filter((_, idx) => idx !== i) })}
              />
            ))}
            <Button type="button" size="sm" variant="ghost" icon={<Plus size={14} />} onClick={adicionarCampo} style={{ justifySelf: 'start' }}>
              Adicionar Campo
            </Button>
          </div>
        ) : (
          <div style={{ display: 'grid', gap: 'var(--s-3)' }}>
            {(area.age_brackets ?? []).map((faixa, i) => (
              <AgeBracketEditor
                key={i}
                bracket={faixa}
                onChange={(b) => {
                  const faixas = [...(area.age_brackets ?? [])]
                  faixas[i] = b
                  onChange({ ...area, age_brackets: faixas })
                }}
                onRemove={() => onChange({ ...area, age_brackets: (area.age_brackets ?? []).filter((_, idx) => idx !== i) })}
              />
            ))}
            <Button type="button" size="sm" variant="ghost" icon={<Plus size={14} />} onClick={adicionarFaixaEtaria} style={{ justifySelf: 'start' }}>
              Adicionar Faixa Etária
            </Button>
          </div>
        )}
      </div>
    </Card>
  )
}

function AgeBracketEditor({
  bracket,
  onChange,
  onRemove,
}: {
  bracket: AgeBracket
  onChange: (bracket: AgeBracket) => void
  onRemove: () => void
}) {
  function adicionarCampo() {
    const novo: TemplateField = { key: slugify(`item_${bracket.fields.length + 1}`), label: `Item ${bracket.fields.length + 1}`, type: 'select', options: ['sim', 'as_vezes', 'nao'], weight: 1 }
    onChange({ ...bracket, fields: [...bracket.fields, novo] })
  }

  return (
    <Card padding="var(--s-3)" style={{ boxShadow: 'none', border: '1px dashed var(--n-300)' }}>
      <div style={{ display: 'grid', gap: 'var(--s-2)' }}>
        <div style={{ display: 'flex', gap: 'var(--s-3)', alignItems: 'flex-end' }}>
          <Input label="Nome Da Faixa" value={bracket.label} onChange={(e) => onChange({ ...bracket, label: e.target.value })} style={{ flex: 1 }} />
          <Input
            label="Idade Máxima (Meses)"
            type="number"
            value={bracket.max_age_months}
            onChange={(e) => onChange({ ...bracket, max_age_months: Number(e.target.value) })}
            style={{ width: 160 }}
          />
          <IconButton label="Remover faixa" icon={<Trash2 size={16} />} variant="secondary" onClick={onRemove} />
        </div>
        {bracket.fields.map((campo, i) => (
          <FieldEditor
            key={i}
            field={campo}
            onChange={(f) => {
              const campos = [...bracket.fields]
              campos[i] = f
              onChange({ ...bracket, fields: campos })
            }}
            onRemove={() => onChange({ ...bracket, fields: bracket.fields.filter((_, idx) => idx !== i) })}
          />
        ))}
        <Button type="button" size="sm" variant="ghost" icon={<Plus size={14} />} onClick={adicionarCampo} style={{ justifySelf: 'start' }}>
          Adicionar Item
        </Button>
      </div>
    </Card>
  )
}

function FieldEditor({
  field,
  onChange,
  onRemove,
}: {
  field: TemplateField
  onChange: (field: TemplateField) => void
  onRemove: () => void
}) {
  return (
    <div style={{ display: 'flex', gap: 'var(--s-2)', alignItems: 'flex-end', flexWrap: 'wrap', padding: 'var(--s-2)', background: 'var(--bg-card)', borderRadius: 'var(--r-sm)' }}>
      <Input label="Pergunta" value={field.label} onChange={(e) => onChange({ ...field, label: e.target.value })} style={{ flex: 2, minWidth: 160 }} />
      <Select
        label="Tipo"
        value={field.type}
        onChange={(e) => onChange({ ...field, type: e.target.value as FieldType })}
        options={TIPOS_DE_CAMPO}
        style={{ minWidth: 170 }}
      />
      {field.type === 'scale' && (
        <>
          <Input label="Mín." type="number" value={field.min ?? 0} onChange={(e) => onChange({ ...field, min: Number(e.target.value) })} style={{ width: 90 }} />
          <Input label="Máx." type="number" value={field.max ?? 4} onChange={(e) => onChange({ ...field, max: Number(e.target.value) })} style={{ width: 90 }} />
          <Input
            label="Peso"
            type="number"
            value={field.weight}
            onChange={(e) => onChange({ ...field, weight: Number(e.target.value) })}
            style={{ width: 90 }}
          />
        </>
      )}
      {field.type === 'select' && (
        <Input
          label="Opções (Separadas Por Vírgula)"
          value={(field.options ?? []).join(', ')}
          onChange={(e) => onChange({ ...field, options: e.target.value.split(',').map((o) => o.trim()).filter(Boolean) })}
          style={{ flex: 2, minWidth: 200 }}
        />
      )}
      <IconButton label="Remover campo" icon={<Trash2 size={16} />} variant="ghost" onClick={onRemove} />
    </div>
  )
}

function ClassificationRangeEditor({
  ruleType,
  areaKeys,
  range,
  onChange,
  onRemove,
}: {
  ruleType: TemplateSchemaJSON['rule_type']
  areaKeys: string[]
  range: ClassificationRange
  onChange: (range: ClassificationRange) => void
  onRemove: () => void
}) {
  return (
    <div style={{ display: 'flex', gap: 'var(--s-2)', alignItems: 'flex-end', flexWrap: 'wrap', padding: 'var(--s-2)', background: 'var(--n-50)', borderRadius: 'var(--r-sm)' }}>
      <Input label="Nome Da Classificação" value={range.label} onChange={(e) => onChange({ ...range, label: e.target.value })} style={{ flex: 1, minWidth: 160 }} />

      {ruleType === 'count_threshold' ? (
        <>
          <Select
            label="Área"
            value={range.area ?? ''}
            onChange={(e) => onChange({ ...range, area: e.target.value })}
            options={areaKeys.map((k) => ({ value: k, label: k }))}
            style={{ minWidth: 160 }}
          />
          <Select
            label="Comparação"
            value={range.comparison ?? 'gte'}
            onChange={(e) => onChange({ ...range, comparison: e.target.value as ComparisonOperator })}
            options={COMPARACOES}
            style={{ minWidth: 180 }}
          />
          <Input
            label="Quantidade Mínima"
            type="number"
            value={range.minimum_count ?? 0}
            onChange={(e) => onChange({ ...range, minimum_count: Number(e.target.value) })}
            style={{ width: 140 }}
          />
        </>
      ) : (
        <>
          <Input label="Mín." type="number" value={range.min ?? 0} onChange={(e) => onChange({ ...range, min: Number(e.target.value) })} style={{ width: 100 }} />
          <Input label="Máx." type="number" value={range.max ?? 0} onChange={(e) => onChange({ ...range, max: Number(e.target.value) })} style={{ width: 100 }} />
        </>
      )}
      <IconButton label="Remover faixa" icon={<Trash2 size={16} />} variant="ghost" onClick={onRemove} />
    </div>
  )
}

function ItemScoringEditor({
  value,
  onChange,
}: {
  value: Record<string, number>
  onChange: (value: Record<string, number>) => void
}) {
  const entradas = Object.entries(value)

  function adicionar() {
    onChange({ ...value, [`resposta_${entradas.length + 1}`]: 1 })
  }

  function atualizarChave(chaveAntiga: string, chaveNova: string) {
    const novo = { ...value }
    const peso = novo[chaveAntiga]
    delete novo[chaveAntiga]
    novo[chaveNova] = peso
    onChange(novo)
  }

  function atualizarPeso(chave: string, peso: number) {
    onChange({ ...value, [chave]: peso })
  }

  function remover(chave: string) {
    const novo = { ...value }
    delete novo[chave]
    onChange(novo)
  }

  return (
    <div>
      <span style={{ font: 'var(--type-label)', color: 'var(--text)', display: 'block', marginBottom: 'var(--s-2)' }}>
        Peso De Cada Resposta Possível
      </span>
      <div style={{ display: 'grid', gap: 'var(--s-2)' }}>
        {entradas.map(([chave, peso]) => (
          <div key={chave} style={{ display: 'flex', gap: 'var(--s-2)', alignItems: 'flex-end' }}>
            <Input label="Resposta" value={chave} onChange={(e) => atualizarChave(chave, e.target.value)} style={{ width: 180 }} />
            <Input label="Peso" type="number" value={peso} onChange={(e) => atualizarPeso(chave, Number(e.target.value))} style={{ width: 100 }} />
            <IconButton label="Remover" icon={<Trash2 size={16} />} variant="ghost" onClick={() => remover(chave)} />
          </div>
        ))}
        <Button type="button" size="sm" variant="ghost" icon={<Plus size={14} />} onClick={adicionar} style={{ justifySelf: 'start' }}>
          Adicionar Resposta
        </Button>
      </div>
    </div>
  )
}
