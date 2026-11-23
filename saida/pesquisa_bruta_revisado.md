TÍTULO: Determinação experimental da constante de Planck através do efeito fotoelétrico

# RESUMO
O presente trabalho teve como objetivo determinar experimentalmente o valor da constante de Planck por meio da análise do efeito fotoelétrico em ambiente de laboratório didático. O experimento utilizou uma lâmpada de vapor de mercúrio como fonte luminosa, uma rede de difração e uma fotocélula com catodo de potássio. Foram mensurados os potenciais de corte para cinco linhas espectrais (365,0 nm, 404,7 nm, 435,8 nm, 546,1 nm e 577,0 nm). A partir do ajuste linear por mínimos quadrados da tensão de corte em função da frequência da luz incidente, obteve-se o valor experimental para a constante de Planck de (6,49 ± 0,09) × 10⁻³⁴ J·s, apresentando um erro percentual de 2,0% em relação ao valor de referência exato estabelecido pelo Sistema Internacional de Unidades. Além disso, a função trabalho do material fotossensível foi calculada em 1,90 eV, confirmando a frequência de corte na região do vermelho. Os resultados apresentaram alta correlação linear (R² = 0,9994), validando a teoria proposta por Einstein e a natureza quântica da radiação eletromagnética.

Palavras-chave: constante de Planck; efeito fotoelétrico; fótons; função trabalho; quantização da energia.

# ABSTRACT
The present work aimed to experimentally determine the value of Planck's constant through the analysis of the photoelectric effect in an educational laboratory environment. The experiment used a mercury vapor lamp as a light source, a diffraction grating, and a photocell with a potassium cathode. Stopping potentials were measured for five spectral lines (365.0 nm, 404.7 nm, 435.8 nm, 546.1 nm, and 577.0 nm). From the linear fit using least squares of the stopping voltage as a function of the frequency of incident light, the experimental value for Planck's constant was obtained as (6.49 ± 0.09) × 10⁻³⁴ J·s, showing a percentage error of 2.0% relative to the exact reference value established by the International System of Units. Furthermore, the work function of the photosensitive material was calculated to be 1.90 eV, confirming the cutoff frequency in the red region. The results demonstrated high linear correlation (R² = 0.9994), validating the theory proposed by Einstein and the quantum nature of electromagnetic radiation.

Keywords: Planck's constant; photoelectric effect; photons; work function; energy quantization.

# Introdução

A constante de Planck é uma das constantes fundamentais mais importantes da física moderna, estando presente na descrição de praticamente todos os fenômenos quânticos. Em 1900, Max Planck propôs que a energia da radiação emitida por um corpo negro era quantizada, ou seja, só podia assumir valores múltiplos de uma quantidade mínima, marco inicial da mecânica quântica (Planck, 1901). A lei de Planck para a densidade de energia espectral é expressa por:

$$u(\lambda, T) = \frac{8\pi hc}{\lambda^5} \frac{1}{e^{\frac{hc}{\lambda kT}} - 1}$$ {#eq:planck}

em que h é a constante de Planck, c é a velocidade da luz no vácuo, k = 1,380649 × 10⁻²³ J/K é a constante de Boltzmann e T é a temperatura absoluta.

Anos mais tarde, Einstein (1905) postulou que a própria luz é constituída por quanta de energia, denominados fótons. Cada fóton possui energia dada por:

$$E = hf$$ {#eq:energia_foton}

sendo f a frequência da radiação. Essa hipótese explicou com êxito o efeito fotoelétrico, o qual a física clássica não conseguia fundamentar, pois, pela teoria eletromagnética clássica, a energia dos elétrons emitidos deveria depender da intensidade da luz e não de sua frequência. Millikan (1916), visando testar a teoria de Einstein, realizou medições de alta precisão e confirmou a Equação [[eq:energia_foton]], obtendo h = 6,57 × 10⁻³⁴ J·s.

O objetivo deste trabalho é determinar experimentalmente o valor da constante de Planck em nível de laboratório didático, utilizando uma lâmpada de mercúrio e uma fotocélula, comparando o resultado com o valor de referência h = 6,62607015 × 10⁻³⁴ J·s, definido como exato após a redefinição do Sistema Internacional de Unidades (SI) em 2019.

# Fundamentação teórica

## O efeito fotoelétrico

Quando a luz de frequência suficientemente alta incide sobre uma superfície metálica, elétrons são emitidos dessa superfície. A energia cinética máxima dos elétrons emitidos é descrita pela equação de Einstein:

$$K_{\text{máx}} = hf - \varphi$$ {#eq:einstein_fotoelétrico}

em que φ é a função trabalho do metal, correspondente à energia mínima necessária para arrancar um elétron (Eisberg; Resnick, 1979). Existe, portanto, uma frequência de corte f₀ abaixo da qual não ocorre emissão fotoelétrica:

$$f_0 = \frac{\varphi}{h}$$ {#eq:frequencia_corte}

A frequência relaciona-se ao comprimento de onda pela equação da onda:

$$c = \lambda f$$ {#eq:onda}

Ao aplicar um potencial retardador entre o catodo e o anodo da fotocélula, a corrente fotocétrica anula-se quando a energia potencial elétrica iguala a energia cinética máxima dos fotoelétrons, isto é, eV₀ = K_máx, onde V₀ é o potencial de corte e e = 1,602176634 × 10⁻¹⁹ C é a carga elementar. Combinando as equações, obtém-se:

$$V_0 = \left(\frac{h}{e}\right)f - \frac{\varphi}{e}$$ {#eq:potencial_corte}

Dessa forma, o gráfico do potencial de corte V₀ em função da frequência f é representado por uma reta cujo coeficiente angular é dado por h/e e o coeficiente linear por -φ/e (Halliday; Resnick; Walker, 2016). Conforme salienta Nussenzveig (2014), essa relação linear constitui uma das evidências mais diretas da quantização da luz.

## Regressão linear

Para a obtenção dos coeficientes da reta, aplicou-se o método dos mínimos quadrados, no qual o coeficiente angular a e o coeficiente linear b são dados, respectivamente, por:

$$a = \frac{n \sum (x y) - \sum x \sum y}{n \sum (x^2) - (\sum x)^2}$$ {#eq:coef_angular}

$$b = \frac{\sum y - a \sum x}{n}$$ {#eq:coef_linear}

A qualidade do ajuste linear foi avaliada pelo coeficiente de determinação:

$$R^2 = 1 - \frac{\sum (y_i - y_{\text{ajuste}})^2}{\sum (y_i - y_{\text{média}})^2}$$ {#eq:r_quadrado}

# Metodologia

O experimento foi realizado no laboratório de física moderna utilizando uma lâmpada de vapor de mercúrio, uma rede de difração com 600 linhas/mm, uma fotocélula composta por catodo de potássio e um voltímetro digital com resolução de 0,01 V. Selecionaram-se cinco linhas espectrais do mercúrio: ultravioleta (365,0 nm), violeta (404,7 nm), azul (435,8 nm), verde (546,1 nm) e amarelo (577,0 nm). Para as linhas verde e amarela, utilizaram-se filtros ópticos a fim de eliminar a sobreposição de ordens superiores de difração da rede.

Para cada linha espectral, o potencial de corte foi medido cinco vezes, ajustando-se a tensão até a corrente fotocétrica anular-se. Para a linha ultravioleta, por exemplo, os valores obtidos foram 1,44 V, 1,42 V, 1,43 V, 1,45 V e 1,41 V, resultando em uma média de 1,43 V e desvio-padrão de 0,016 V. A frequência f associada a cada comprimento de onda foi calculada considerando c = 2,998 × 10⁸ m/s por meio da Equação [[eq:onda]].

# Resultados e discussão

Os valores médios observados e calculados encontram-se resumidos na Tabela [[tab:dados_medidos]].

Tabela: Dados experimentais medidos para as linhas espectrais do mercúrio {#tab:dados_medidos}

| Cor | λ (nm) | f (10¹⁴ Hz) | V₀ (V) |
| :--- | :---: | :---: | :---: |
| Ultravioleta | 365,0 | 8,214 | 1,43 |
| Violeta | 404,7 | 7,408 | 1,12 |
| Azul | 435,8 | 6,879 | 0,87 |
| Verde | 546,1 | 5,490 | 0,33 |
| Amarelo | 577,0 | 5,196 | 0,21 |

Fonte: Elaborada pelo autor.

Por meio da regressão linear do potencial de corte V₀ em função da frequência f, obtiveram-se os parâmetros a = 4,05 × 10⁻¹⁵ V·s e b = -1,90 V, apresentando um coeficiente de determinação R² = 0,9994. A constante de Planck foi calculada a partir da relação:

$$h = a \cdot e$$ {#eq:calculo_h}

obtendo-se o valor experimental h = 6,49 × 10⁻³⁴ J·s. A incerteza associada foi propagada segundo a equação:

$$\sigma_h = e \cdot \sigma_a$$ {#eq:propaga_erro}

Considerando σ_a = 0,06 × 10⁻¹⁵ V·s, encontrou-se σ_h = 0,09 × 10⁻³⁴ J·s. O erro percentual relativo ao valor de referência foi determinado por:

$$\text{Erro} = \frac{|h_{\text{exp}} - h_{\text{ref}}|}{h_{\text{ref}}} \times 100\%$$ {#eq:erro_percentual}

resultando em 2,0%, o que demonstra boa concordância experimental, muito embora o valor final tenha se situado ligeiramente abaixo da referência. A função trabalho extraída do coeficiente linear correspondeu a φ = -b·e = 1,90 eV. O comprimento de onda de corte limiar associado foi determinado por:

$$\lambda_c = \frac{hc}{\varphi}$$ {#eq:lambda_corte}

resultando em aproximadamente 640 nm, o que indica que fótons da região do vermelho não possuem energia suficiente para emitir elétrons desse catodo, fato verificado na prática.

As principais fontes de incerteza do experimento atribuem-se à determinação visual da nuança de corrente nula, à presença de corrente reversa no anodo e à interferência da luz ambiente. Ademais, observou-se baixa intensidade luminosa na linha amarela, o que elevou a dificuldade das medições para essa frequência específica.

# Conclusão

O procedimento experimental permitiu a determinação da constante de Planck com um erro relativo de 2,0%. O valor experimental obtido, (6,49 ± 0,09) × 10⁻³⁴ J·s, mostra-se compatível com o valor de referência aceito, situando-se dentro do intervalo de 1,5 desvios-padrão. Os resultados confirmam a dependência linear entre a frequência da luz e a energia cinética dos fotoelétrons postulada por Einstein, bem como a natureza quântica da radiação. Em trabalhos futuros, recomenda-se a inclusão de um amplificador de corrente de precisão e a utilização de um número maior de linhas espectrais com o intuito de diminuir as incertezas experimentais.

# REFERÊNCIAS
EISBERG, R.; RESNICK, R. **Física quântica: átomos, moléculas, sólidos, núcleos e partículas**. Rio de Janeiro: Campus, 1979.
EINSTEIN, A. Über einen die Erzeugung und Verwandlung des Lichtes betreffenden heuristischen Gesichtspunkt. **Annalen der Physik**, v. 322, n. 6, p. 132-148, 1905. DOI: 10.1002/andp.19053220607.
HALLIDAY, D.; RESNICK, R.; WALKER, J. **Fundamentos de física: ótica e física moderna**. 10. ed. Rio de Janeiro: LTC, 2016. v. 4.
MILLIKAN, R. A. A Direct Photoelectric Determination of Planck's "h". **Physical Review**, v. 7, n. 3, p. 355-388, 1916. DOI: 10.1103/physrev.7.355.
NUSSENZVEIG, H. M. **Curso de física básica: ótica, relatividade, física quântica**. 2. ed. São Paulo: Blucher, 2014. v. 4.
PLANCK, M. Ueber das Gesetz der Energieverteilung im Normalspectrum. **Annalen der Physik**, v. 309, n. 3, p. 553-563, 1901. DOI: 10.1002/andp.19013090310.