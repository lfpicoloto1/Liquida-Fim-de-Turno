import type { Metadata } from "next";
import { LegalDocShell } from "@/components/legal-doc-shell";

export const metadata: Metadata = {
  title: "Termos de uso | Liquida Fim de Turno",
  description: "Condições de uso do Liquida Fim de Turno para lojistas aiqfome.",
};

const UPDATED = "9 de abril de 2026";

export default function TermosPage() {
  return (
    <LegalDocShell title="Termos de uso" lastUpdated={UPDATED}>
      <p>
        Estes termos regem o uso da aplicação <strong>Liquida Fim de Turno</strong> (“serviço”). Ao utilizar o serviço,
        você declara que leu e concorda com o disposto abaixo. O texto é modelo operacional; valide com assessoria
        jurídica antes de publicação definitiva.
      </p>

      <h2>1. O que é o serviço</h2>
      <p>
        O Liquida Fim de Turno é uma ferramenta para <strong>lojistas da plataforma aiqfome</strong> configurarem
        descontos automáticos em janela próxima ao fechamento da loja, com integração a identidade Magalu e APIs
        aiqfome, conforme disponibilidade técnica da sua implantação.
      </p>

      <h2>2. Elegibilidade e conta</h2>
      <p>
        Você precisa ter capacidade legal para contratar em nome da loja e possuir credenciais válidas (Magalu ID e
        permissões na aiqfome). É responsável pela veracidade das informações e pela segurança da sua sessão e
        dispositivos.
      </p>

      <h2>3. Uso aceitável</h2>
      <ul>
        <li>Não utilizar o serviço para violar lei, direitos de terceiros ou políticas da aiqfome / Magalu.</li>
        <li>Não tentar acessar dados de outras lojas, contornar autenticação ou sobrecarregar sistemas de forma abusiva.</li>
        <li>Não enganar consumidores sobre preços, disponibilidade ou condições da promoção.</li>
      </ul>

      <h2>4. Integrações e API</h2>
      <p>
        Funcionalidades dependem da <strong>disponibilidade e dos termos da API aiqfome</strong>, do Magalu ID e de
        serviços de infraestrutura. Alterações nas APIs de terceiros podem impactar o comportamento do produto sem aviso
        prévio do nosso lado.
      </p>

      <h2>5. Efeitos da promoção</h2>
      <p>
        Você é responsável pelas <strong>consequências comerciais e fiscais</strong> das promoções configuradas
        (preços exibidos ao consumidor, estoque, comunicação na loja, etc.). O serviço atua como ferramenta de apoio; a
        decisão final sobre descontos e operação é sua.
      </p>

      <h2>6. Disponibilidade e suporte</h2>
      <p>
        O serviço é fornecido <strong>“no estado em que se encontra”</strong>, sem garantia de disponibilidade
        ininterrupta. Manutenções, incidentes de rede ou de terceiros podem causar indisponibilidade temporária.
      </p>

      <h2>7. Limitação de responsabilidade</h2>
      <p>
        Na máxima extensão permitida pela lei aplicável, não nos responsabilizamos por lucros cessantes, perdas
        indiretas ou danos decorrentes do uso ou impossibilidade de uso do serviço, salvo dolo ou culpa grave, conforme
        ordenamento jurídico brasileiro.
      </p>

      <h2>8. Propriedade intelectual</h2>
      <p>
        Marcas, layout e código do produto pertencem aos respectivos titulares. É vedada cópia, engenharia reversa ou
        uso não autorizado além do necessário ao uso normal do serviço.
      </p>

      <h2>9. Alterações dos termos</h2>
      <p>
        Podemos atualizar estes termos. A data no topo indica a última revisão. Quando a mudança for material,
        recomendamos comunicar usuários pelo próprio app ou por outros canais do operador.
      </p>

      <h2>10. Lei e foro</h2>
      <p>
        Aplica-se a <strong>legislação da República Federativa do Brasil</strong>. Fica eleito o foro da comarca do
        domicílio do consumidor ou, tratando-se de pessoa jurídica, o competente na forma da lei, salvo disposição
        específica em contrato com o operador do serviço.
      </p>
    </LegalDocShell>
  );
}
