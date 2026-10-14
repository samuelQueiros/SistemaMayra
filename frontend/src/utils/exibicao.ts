// Formatação só para exibir na tela — nunca altera o dado salvo.

const PARTICULAS = new Set(['da', 'das', 'de', 'do', 'dos', 'e', 'di', 'du', 'del', 'van', 'von'])

const capitalizar = (parte: string) => parte.charAt(0).toLocaleUpperCase('pt-BR') + parte.slice(1)

/** Nome do paciente como nome ("ANA DE SOUZA" → "Ana de Souza"). Nomes já
 * digitados com maiúsculas e minúsculas ficam como estão. */
export function nomeParaExibicao(nome: string | null | undefined): string {
  const texto = (nome ?? '').trim().replace(/\s+/g, ' ')
  if (!texto || texto !== texto.toLocaleUpperCase('pt-BR')) return texto
  return texto
    .toLocaleLowerCase('pt-BR')
    .split(' ')
    .map((palavra, i) =>
      i > 0 && PARTICULAS.has(palavra) ? palavra : palavra.split(/([-'’])/).map((p) => (/[-'’]/.test(p) ? p : capitalizar(p))).join(''),
    )
    .join(' ')
}

/** Idade a partir da data de nascimento (AAAA-MM-DD): "7 anos", "1 ano e 3 meses", "8 meses". */
export function idadeParaExibicao(dataNascimento: string | null | undefined, hoje = new Date()): string {
  if (!dataNascimento) return ''
  const nascimento = new Date(`${dataNascimento}T00:00:00`)
  if (Number.isNaN(nascimento.getTime())) return ''
  let meses = (hoje.getFullYear() - nascimento.getFullYear()) * 12 + hoje.getMonth() - nascimento.getMonth()
  if (hoje.getDate() < nascimento.getDate()) meses--
  if (meses < 0) return ''
  const anos = Math.floor(meses / 12)
  const resto = meses % 12
  if (anos === 0) return `${resto} ${resto === 1 ? 'mês' : 'meses'}`
  const textoAnos = `${anos} ${anos === 1 ? 'ano' : 'anos'}`
  return anos < 3 && resto ? `${textoAnos} e ${resto} ${resto === 1 ? 'mês' : 'meses'}` : textoAnos
}
