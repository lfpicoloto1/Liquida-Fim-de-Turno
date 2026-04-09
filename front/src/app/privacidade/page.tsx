import type { Metadata } from "next";
import { LegalDocShell } from "@/components/legal-doc-shell";

export const metadata: Metadata = {
  title: "Política de privacidade | Liquida Fim de Turno",
  description:
    "Como tratamos dados pessoais no Liquida Fim de Turno (promoção de fim de expediente para lojistas aiqfome).",
};

const UPDATED = "9 de abril de 2026";

export default function PrivacidadePage() {
  return (
    <LegalDocShell title="Política de privacidade" lastUpdated={UPDATED}>
      <p>
        Esta política descreve como o serviço <strong>Liquida Fim de Turno</strong> (“serviço”, “nós”) trata dados
        pessoais na operação da aplicação web voltada a <strong>lojistas da plataforma aiqfome</strong> que configuram
        promoções automáticas próximas ao fechamento. O texto é informativo; ajuste com assessoria jurídica antes de uso
        formal em produção.
      </p>

      <h2>1. Quem é o responsável</h2>
      <p>
        O responsável pelo tratamento é a pessoa jurídica ou equipe que opera a instância do serviço que você utiliza
        (incluindo hospedagem, domínio e suporte). Em caso de dúvidas sobre privacidade, utilize o canal de contato
        divulgado pela sua contratante ou operador do produto.
      </p>

      <h2>2. Quais dados podemos tratar</h2>
      <ul>
        <li>
          <strong>Dados de autenticação Magalu ID:</strong> identificadores e tokens necessários para validar sua sessão
          e acessar integrações autorizadas (conforme escopos concedidos no login).
        </li>
        <li>
          <strong>Dados da loja na aiqfome:</strong> identificadores da loja, nome de exibição, fuso horário e
          informações obtidas via API aiqfome quando você está autenticado (ex.: horários, categorias e itens do
          cardápio para configurar a promoção).
        </li>
        <li>
          <strong>Configurações da rotina:</strong> percentual de desconto, antecedência ao fechamento, dias da semana,
          categorias elegíveis e preferências salvas na aplicação.
        </li>
        <li>
          <strong>Dados técnicos:</strong> logs de acesso, endereço IP, agente do navegador, carimbos de data/hora e
          registros de erro, para segurança, diagnóstico e continuidade do serviço.
        </li>
      </ul>

      <h2>3. Finalidades</h2>
      <ul>
        <li>Prestação do serviço de configuração e orquestração da promoção de fim de expediente.</li>
        <li>Autenticação, autorização e integração com Magalu ID e API aiqfome conforme o que você aprovar.</li>
        <li>Segurança, prevenção a fraudes e cumprimento de obrigações legais aplicáveis.</li>
        <li>Melhoria técnica e suporte, de forma agregada sempre que possível.</li>
      </ul>

      <h2>4. Bases legais (LGPD)</h2>
      <p>
        Dependendo do caso, o tratamento pode se basear na <strong>execução de contrato</strong> ou procedimentos
        preliminares, no <strong>legítimo interesse</strong> (segurança e melhoria do serviço, com balanceamento de
        direitos), no <strong>consentimento</strong> quando exigido (ex.: cookies não essenciais, se aplicável) e no
        cumprimento de <strong>obrigação legal</strong>.
      </p>

      <h2>5. Compartilhamento</h2>
      <p>
        Podemos enviar dados a <strong>provedores de infraestrutura</strong> (hospedagem, banco de dados, filas de
        trabalho) e a <strong>terceiros estritamente necessários</strong> à operação: Magalu / ecossistema de identidade
        autorizado, API aiqfome, e serviços de orquestração (ex.: Temporal) configurados na sua implantação. Não
        vendemos seus dados pessoais.
      </p>

      <h2>6. Retenção</h2>
      <p>
        Mantemos dados pelo tempo necessário para cumprir as finalidades acima, respeitando prazos legais e políticas de
        backup. Configurações e registros operacionais podem ser apagados ou anonimizados quando não forem mais
        necessários, conforme processo interno do operador.
      </p>

      <h2>7. Seus direitos</h2>
      <p>
        Nos termos da LGPD, você pode solicitar confirmação de tratamento, acesso, correção, anonimização, eliminação,
        portabilidade (quando aplicável), informação sobre compartilhamentos e revisão de decisões automatizadas. Para
        exercer direitos, entre em contato pelo canal indicado pelo operador do serviço.
      </p>

      <h2>8. Segurança</h2>
      <p>
        Adotamos medidas técnicas e organizacionais razoáveis para proteger dados (ex.: conexões criptografadas,
        segregação de segredos, controles de acesso). Nenhum sistema é isento de risco.
      </p>

      <h2>9. Alterações</h2>
      <p>
        Esta política pode ser atualizada. A data no topo indica a última revisão relevante. Uso continuado após aviso
        pode significar concordância com a versão vigente, conforme aplicável.
      </p>
    </LegalDocShell>
  );
}
