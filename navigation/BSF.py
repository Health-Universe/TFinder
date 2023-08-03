# Copyright (c) 2023 Minniti Julien

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of TFinder and associated documentation files, to deal
# in TFinder without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of TFinder, and to permit persons to whom TFinder is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of TFinder.

# TFINDER IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH TFINDER OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import streamlit as st
import requests
import pandas as pd
import altair as alt
import math
import pickle
import numpy as np
import json
import logomaker
import random
import io
from openpyxl import Workbook
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
import base64
import datetime
import matplotlib.pyplot as plt
from PIL import Image

def BSF_page():
    # Promoter output state

    st.subheader('🔎 Binding Sites Finder')
    st.markdown("🔸 :orange[**Step 2.1**] Sequences:")
    result_promoter = st.text_area("🔸 :red[**Step 1.1**] Sequence:", value="Paste sequences here (FASTA required for multiple sequences).", label_visibility='collapsed')
        
    # Extract JASPAR matrix
    def matrix_extraction(sequence_consensus_input):
        jaspar_id = sequence_consensus_input
        url = f"https://jaspar.genereg.net/api/v1/matrix/{jaspar_id}/"
        response = requests.get(url)
        if response.status_code == 200:
            response_data = response.json()
            matrix = response_data['pfm']
        else:
            messagebox.showerror("Erreur", f"Erreur lors de la récupération de la matrice de fréquence : {response.status_code}")
            return

        return transform_matrix(matrix)

    # Transform JASPAR matrix
    def transform_matrix(matrix):
        reversed_matrix = {base: list(reversed(scores)) for base, scores in matrix.items()}
        complement_matrix = {
            'A': matrix['T'],
            'C': matrix['G'],
            'G': matrix['C'],
            'T': matrix['A']
        }
        reversed_complement_matrix = {base: list(reversed(scores)) for base, scores in complement_matrix.items()}

        return {
            'Original': matrix,
            'Reversed': reversed_matrix,
            'Complement': complement_matrix,
            'Reversed Complement': reversed_complement_matrix
        }

    # Calculate score with JASPAR
    def calculate_score(sequence, matrix):
        score = 0
        for i, base in enumerate(sequence):
            if base in {'A', 'C', 'G', 'T'}:
                base_score = matrix[base]
                score += base_score[i]
        return score

    # Find sequence in promoter
    def search_sequence(threshold, tis_value, result_promoter, matrices):
        global table2
        table2 = []
        
        # Promoter input type
        lines = result_promoter
        promoters = []

        first_line = lines
        if first_line.startswith(("A", "T", "C", "G")):
            shortened_promoter_name = "n.d."
            promoter_region = lines
            region = "n.d"
            promoters.append((shortened_promoter_name, promoter_region, region))
        else:
            lines = result_promoter.split("\n")
            i = 0
            while i < len(lines):
                line = lines[i]
                if line.startswith(">"):
                    promoter_name = line[1:]
                    shortened_promoter_name = promoter_name[:15] if len(promoter_name) > 10 else promoter_name
                    if "promoter" in promoter_name.lower():
                        region = "Prom."
                    elif "terminator" in promoter_name.lower():
                        region = "Term."
                    else:
                        region = "n.d"
                    promoter_region = lines[i + 1]
                    promoters.append((shortened_promoter_name, promoter_region, region))
                    i += 2
                else:
                    i += 1
        
        if calc_pvalue:
            for matrix_name, matrix in matrices.items():
                seq_length = len(matrix['A'])
            
            for shortened_promoter_name, promoter_region, region in promoters:
                length_prom = len(promoter_region)
                        
                def generate_random_sequence(length, probabilities):
                    nucleotides = ['A', 'C', 'G', 'T']
                    sequence = random.choices(nucleotides, probabilities, k=length)
                    return ''.join(sequence)

                # Generate random sequences
                motif_length = seq_length
                num_random_seqs = 1000000

                count_a = promoter_region.count('A')
                count_t = promoter_region.count('T')
                count_g = promoter_region.count('G')
                count_c = promoter_region.count('C')

                length_prom = len(promoter_region)
                percentage_a = count_a / length_prom
                percentage_t = count_t / length_prom
                percentage_g = count_g / length_prom
                percentage_c = count_c / length_prom

                probabilities = [percentage_a, percentage_c, percentage_g, percentage_t]

                random_sequences = []
                for _ in range(num_random_seqs):
                    random_sequence = generate_random_sequence(motif_length, probabilities)
                    random_sequences.append(random_sequence)

                # Calculation of random scores from the different matrices
                random_scores = {}
        
        for matrix_name, matrix in matrices.items():
            seq_length = len(matrix['A'])

            # Max score per matrix
            max_score = sum(max(matrix[base][i] for base in matrix.keys()) for i in range(seq_length))
            min_score = sum(min(matrix[base][i] for base in matrix.keys()) for i in range(seq_length))

            # REF
            for shortened_promoter_name, promoter_region, region in promoters:
                found_positions = []
                length_prom = len(promoter_region)

                if calc_pvalue :
                    
                    matrix_random_scores = []
                    for random_sequence in random_sequences:
                        random_score = calculate_score(random_sequence, matrix)
                        normalized_random_score = (random_score - min_score) / (max_score - min_score)
                        matrix_random_scores.append(normalized_random_score)

                    random_scores = np.array(matrix_random_scores)

                for i in range(len(promoter_region) - seq_length + 1):
                    seq = promoter_region[i:i + seq_length]
                    score = calculate_score(seq, matrix)
                    normalized_score = (score - min_score)/(max_score - min_score)
                    position = int(i)
                    
                    if calc_pvalue : 
                        p_value = (random_scores >= normalized_score).sum() / num_random_seqs

                        found_positions.append((position, seq, normalized_score, p_value))
                    else :
                        found_positions.append((position, seq, normalized_score))
                    
                # Sort positions in descending order of score percentage
                found_positions.sort(key=lambda x: x[1], reverse=True)

                # Creating a results table
                if len(found_positions) > 0:
                    if calc_pvalue :
                        for position, seq, normalized_score, p_value in found_positions:
                            start_position = max(0, position - 3)
                            end_position = min(len(promoter_region), position + len(seq) + 3)
                            sequence_with_context = promoter_region[start_position:end_position]

                            sequence_parts = []
                            for j in range(start_position, end_position):
                                if j < position or j >= position + len(seq):
                                    sequence_parts.append(sequence_with_context[j - start_position].lower())
                                else:
                                    sequence_parts.append(sequence_with_context[j - start_position].upper())

                            sequence_with_context = ''.join(sequence_parts)
                            tis_position = position - tis_value
                            
                            if normalized_score >= threshold:
                                row = [str(position).ljust(8),
                                       str(tis_position).ljust(15),
                                       sequence_with_context,
                                       "{:.6f}".format(normalized_score).ljust(12), "{:.3e}".format(p_value).ljust(12),
                                       shortened_promoter_name, region]
                                table2.append(row)
                    else:
                        for position, seq, normalized_score in found_positions:
                            start_position = max(0, position - 3)
                            end_position = min(len(promoter_region), position + len(seq) + 3)
                            sequence_with_context = promoter_region[start_position:end_position]

                            sequence_parts = []
                            for j in range(start_position, end_position):
                                if j < position or j >= position + len(seq):
                                    sequence_parts.append(sequence_with_context[j - start_position].lower())
                                else:
                                    sequence_parts.append(sequence_with_context[j - start_position].upper())

                            sequence_with_context = ''.join(sequence_parts)
                            tis_position = position - tis_value
                            
                            if normalized_score >= threshold:
                                row = [str(position).ljust(8),
                                       str(tis_position).ljust(15),
                                       sequence_with_context,
                                       "{:.6f}".format(normalized_score).ljust(12),
                                       shortened_promoter_name, region]
                                table2.append(row)

        if len(table2) > 0:
            if calc_pvalue :
                table2.sort(key=lambda x: float(x[3]), reverse=True)
                header = ["Position", "Rel Position", "Sequence", "Rel Score", "p-value", "Gene", "Region"]
                table2.insert(0, header)
            else:
                table2.sort(key=lambda x: float(x[3]), reverse=True)
                header = ["Position", "Rel Position", "Sequence", "Rel Score", "Gene", "Region"]
                table2.insert(0, header)
            
        else:
            no_consensus = "No consensus sequence found with the specified threshold."
            
        return table2

    # Responsive Elements Finder

    # RE entry
    REcol1, REcol2 = st.columns([0.30,0.70])
    with REcol1:
        st.markdown('🔸 :orange[**Step 2.2**] Responsive elements type:')
        jaspar = st.radio('🔸 :orange[**Step 2.2**] Responsive elements type:', ('Manual sequence','JASPAR_ID','PWM'), label_visibility='collapsed')
    if jaspar == 'JASPAR_ID':
        with REcol1:
            st.markdown("🔸 :orange[**Step 2.3**] JASPAR ID:")
            entry_sequence = st.text_input("🔸 :orange[**Step 2.3**] JASPAR ID:", value="MA0106.1", label_visibility='collapsed')
            url = f"https://jaspar.genereg.net/api/v1/matrix/{entry_sequence}/"
            response = requests.get(url)
            response_data = response.json()
            TF_name = response_data['name']
            TF_species = response_data['species'][0]['name']
            st.success(f"{TF_species} transcription factor {TF_name}")
        with REcol2:
            st.image(f"https://jaspar.genereg.net/static/logos/all/svg/{entry_sequence}.svg")
    elif jaspar == 'PWM':
        with REcol1:
            st.markdown('🔸 :orange[**Step 2.2bis**] Matrix:')
            matrix_type = st.radio('🔸 :orange[**Step 2.2bis**] Matrix:', ('With FASTA sequences','With PWM'), label_visibility='collapsed')
        if matrix_type == 'With PWM':
            isUIPAC = True
            with REcol2:
                st.markdown("🔸 :orange[**Step 2.3**] Matrix:", help="Only PWM generated with our tools are allowed")
                matrix_text = st.text_area("🔸 :orange[**Step 2.3**] Matrix:", value="A [ 20.0 0.0 0.0 0.0 0.0 0.0 0.0 100.0 0.0 60.0 20.0 ]\nT [ 60.0 20.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 ]\nG [ 0.0 20.0 100.0 0.0 0.0 100.0 100.0 0.0 100.0 40.0 0.0 ]\nC [ 20.0 60.0 0.0 100.0 100.0 0.0 0.0 0.0 0.0 0.0 80.0 ]", label_visibility='collapsed')
        else:
            with REcol1:
                st.markdown("🔸 :orange[**Step 2.3**] Sequences:", help='Put FASTA sequences. Same sequence length required ⚠️')
                fasta_text = st.text_area("🔸 :orange[**Step 2.3**] Sequences:", value=">seq1\nCTGCCGGAGGA\n>seq2\nAGGCCGGAGGC\n>seq3\nTCGCCGGAGAC\n>seq4\nCCGCCGGAGCG\n>seq5\nAGGCCGGATCG", label_visibility='collapsed')
            isUIPAC = True
            
             # Generate matrix
            def calculate_pwm(sequences):
                num_sequences = len(sequences) 
                sequence_length = len(sequences[0])
                pwm = np.zeros((4, sequence_length))
                for i in range(sequence_length):
                    counts = {'A': 0, 'T': 0, 'C': 0, 'G': 0}
                    for sequence in sequences:
                        nucleotide = sequence[i]
                        if nucleotide in counts:
                            counts[nucleotide] += 1
                    pwm[0, i] = counts['A'] / num_sequences
                    pwm[1, i] = counts['T'] / num_sequences
                    pwm[2, i] = counts['G'] / num_sequences
                    pwm[3, i] = counts['C'] / num_sequences

                return pwm

            def parse_fasta(fasta_text):
                sequences = []
                current_sequence = ""

                for line in fasta_text.splitlines():
                    if line.startswith(">"):
                        if current_sequence:
                            sequences.append(current_sequence)
                        current_sequence = ""
                    else:
                        current_sequence += line

                if current_sequence:
                    sequences.append(current_sequence)

                return sequences
                
            if fasta_text:
                sequences = parse_fasta(fasta_text)
                sequences = [seq.upper() for seq in sequences]

                if len(sequences) > 0:
                    pwm = calculate_pwm(sequences)
                    bases = ['A', 'T', 'G', 'C']
                    pwm_text = ""
                    for i in range(len(pwm)):
                        base_name = bases[i]
                        base_values = pwm[i]

                        base_str = base_name + " ["
                        for value in base_values:
                            base_str += "\t" + format(value) + "\t" if np.isfinite(value) else "\t" + "NA" + "\t"

                        base_str += "]\n"
                        pwm_text += base_str
                    
                    with REcol2:
                        matrix_text = st.text_area("PWM:", value=pwm_text, help="Select and copy for later use. Don't modify.", key="non_editable_text")

                else:
                    st.warning("You forget FASTA sequences :)")
                
                def create_web_logo(sequences):
                    matrix = logomaker.alignment_to_matrix(sequences)
                    logo = logomaker.Logo(matrix, color_scheme = 'classic')

                    return logo
                
                with REcol2:
                    sequences_text = fasta_text
                    sequences = []
                    current_sequence = ""
                    for line in sequences_text.splitlines():
                        line = line.strip()
                        if line.startswith(">"):
                            if current_sequence:
                                sequences.append(current_sequence)
                            current_sequence = ""
                        else:
                            current_sequence += line

                    if current_sequence:
                        sequences.append(current_sequence)

                    if sequences:
                        logo = create_web_logo(sequences)
                        st.pyplot(logo.fig)
                        buffer = io.BytesIO()
                        plt.savefig(buffer, format='jpg')
                        buffer.seek(0)
          
    else:
        with REcol1:
            st.markdown("🔸 :orange[**Step 2.3**] Responsive element:", help="IUPAC authorized")
            IUPAC = st.text_input("🔸 :orange[**Step 2.3**] Responsive element (IUPAC authorized):", value="GGGRNYYYCC", label_visibility='collapsed')
        
        IUPAC_code = ['A','T','G','C','R','Y','M','K','W','S','B','D','H','V','N']
        
        if all(char in IUPAC_code for char in IUPAC):
            isUIPAC = True
            # IUPAC code
            def generate_iupac_variants(sequence):
                iupac_codes = {
                    "R": ["A", "G"],
                    "Y": ["C", "T"],
                    "M": ["A", "C"],
                    "K": ["G", "T"],
                    "W": ["A", "T"],
                    "S": ["C", "G"],
                    "B": ["C", "G", "T"],
                    "D": ["A", "G", "T"],
                    "H": ["A", "C", "T"],
                    "V": ["A", "C", "G"],
                    "N": ["A", "C", "G", "T"]
                }

                sequences = [sequence]
                for i, base in enumerate(sequence):
                    if base.upper() in iupac_codes:
                        new_sequences = []
                        for seq in sequences:
                            for alternative in iupac_codes[base.upper()]:
                                new_sequence = seq[:i] + alternative + seq[i + 1:]
                                new_sequences.append(new_sequence)
                        sequences = new_sequences

                return sequences
               
            sequences = generate_iupac_variants(IUPAC)
            fasta_text = ""
            for i, seq in enumerate(sequences):
                fasta_text += f">seq{i + 1}\n{seq}\n"
            
             # Generate matrix
            def calculate_pwm(sequences):
                num_sequences = len(sequences)
                sequence_length = len(sequences[0])
                pwm = np.zeros((4, sequence_length))
                for i in range(sequence_length):
                    counts = {'A': 0, 'T': 0, 'C': 0, 'G': 0}
                    for sequence in sequences:
                        nucleotide = sequence[i]
                        if nucleotide in counts:
                            counts[nucleotide] += 1
                    pwm[0, i] = counts['A'] / num_sequences
                    pwm[1, i] = counts['T'] / num_sequences
                    pwm[2, i] = counts['G'] / num_sequences
                    pwm[3, i] = counts['C'] / num_sequences

                return pwm

            def parse_fasta(fasta_text):
                sequences = []
                current_sequence = ""

                for line in fasta_text.splitlines():
                    if line.startswith(">"):
                        if current_sequence:
                            sequences.append(current_sequence)
                        current_sequence = ""
                    else:
                        current_sequence += line

                if current_sequence:
                    sequences.append(current_sequence)

                return sequences
                
            if fasta_text:
                sequences = parse_fasta(fasta_text)
                sequences = [seq.upper() for seq in sequences]

                if len(sequences) > 0:
                    pwm = calculate_pwm(sequences)
                    bases = ['A', 'T', 'G', 'C']
                    pwm_text = ""
                    for i in range(len(pwm)):
                        base_name = bases[i]
                        base_values = pwm[i]

                        base_str = base_name + " ["
                        for value in base_values:
                            base_str += "\t" + format(value) + "\t" if np.isfinite(value) else "\t" + "NA" + "\t"

                        base_str += "]\n"
                        pwm_text += base_str
                    
                    with REcol2:
                        matrix_text = st.text_area("PWM:", value=pwm_text, help="Select and copy for later use. Dont't modify.", key="non_editable_text")

                else:
                    st.warning("You forget FASTA sequences :)")
                
                def create_web_logo(sequences):
                    matrix = logomaker.alignment_to_matrix(sequences)
                    logo = logomaker.Logo(matrix, color_scheme = 'classic')

                    return logo
                
                with REcol2:
                    sequences_text = fasta_text
                    sequences = []
                    current_sequence = ""
                    for line in sequences_text.splitlines():
                        line = line.strip()
                        if line.startswith(">"):
                            if current_sequence:
                                sequences.append(current_sequence)
                            current_sequence = ""
                        else:
                            current_sequence += line

                    if current_sequence:
                        sequences.append(current_sequence)

                    if sequences:
                        logo = create_web_logo(sequences)
                        st.pyplot(logo.fig)
                        buffer = io.BytesIO()
                        plt.savefig(buffer, format='jpg')
                        buffer.seek(0)
        else:
            isUIPAC = False

    # TSS entry
    BSFcol1, BSFcol2, BSFcol3 = st.columns([2,2,1], gap="medium")
    with BSFcol1:
        st.markdown("🔸 :orange[**Step 2.4**] Transcription Start Site (TSS) and gene end at (in bp):", help="Distance of TSS and gene end from begin of sequences. Do not modify if you use Step 1")
        entry_tis = st.number_input("🔸 :orange[**Step 2.4**] Transcription Start Site (TSS) and gene end at (in bp):", -10000, 10000, 0, label_visibility="collapsed")

    # Threshold pvalue
    
    with BSFcol2:
        st.markdown("🔸 :orange[**Step 2.5**] Relative Score threshold")
        threshold_entry = st.slider("🔸 :orange[**Step 2.5**] Relative Score threshold", 0.0, 1.0 ,0.85, step= 0.05, label_visibility="collapsed")
        
    with BSFcol3:
        st.markdown("🔸 :orange[**_Experimental_**] Calcul _p-value_", help='Experimental, take more times')
        calc_pvalue = st.checkbox('_p-value_')

    # Run Responsive Elements finder
    if result_promoter.startswith(("A", "T", "G", "C", ">")):
        with st.spinner("Finding responsive elements..."):
            tis_value = int(entry_tis)
            threshold = float(threshold_entry)
            try:
                if jaspar == 'JASPAR_ID':
                    sequence_consensus_input = entry_sequence
                    matrices = matrix_extraction(sequence_consensus_input)
                    table2 = search_sequence(threshold, tis_value, result_promoter, matrices)
                else:
                    if isUIPAC == False:
                        st.error("Please use IUPAC code for Responsive Elements")
                    else:
                        matrix_lines = matrix_text.split('\n')
                        matrix = {}
                        for line in matrix_lines:
                            line = line.strip()
                            if line:
                                key, values = line.split('[', 1)
                                values = values.replace(']', '').split()
                                values = [float(value) for value in values]
                                matrix[key.strip()] = values
                        matrices = transform_matrix(matrix)
                        table2 = search_sequence(threshold, tis_value, result_promoter, matrices)            
            except Exception as e:
                st.error(f"Error finding responsive elements: {str(e)}")
    
    # RE output
    if jaspar == 'JASPAR_ID':
        if 'table2' in locals():
            if len(table2) > 0:
                current_date_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                st.subheader(':orange[Results]')
                jaspar_id = sequence_consensus_input
                url = f"https://jaspar.genereg.net/api/v1/matrix/{jaspar_id}/"
                response = requests.get(url)
                response_data = response.json()
                TF_name = response_data['name']
                colres1,colres2,colres3, colres4, colres5 = st.columns([1,0.5,0.5,1,1])
                with colres1:
                    st.success(f"Finding responsive elements done for {TF_name}")
                df = pd.DataFrame(table2[1:], columns=table2[0])
                st.session_state['df'] = df
                st.markdown('**Table**')
                st.dataframe(df, hide_index=True)
                with colres2:
                    excel_file = io.BytesIO()
                    df.to_excel(excel_file, index=False, sheet_name='Sheet1')
                    excel_file.seek(0)
                    st.download_button("💾 Download table (.xls)", excel_file, file_name=f'Results_TFinder_{current_date_time}.xlsx', mime="application/vnd.ms-excel", key='download-excel')
                with colres3:
                    txt_output = f"JASPAR_ID: {jaspar_id} | Transcription Factor name: {TF_name}\n\nRelScore Threshold:\n{threshold_entry}\n\nSequences:\n{result_promoter}"
                    st.download_button(label="💾 Download sequences (.txt)",data=txt_output,file_name=f"Sequences_{current_date_time}.txt",mime="text/plain")
            
                source = df
                score_range = source['Rel Score'].astype(float)
                ystart = score_range.min() - 0.02
                ystop = score_range.max() + 0.02
                source['Gene_Region'] = source['Gene'] + " " + source['Region']
                scale = alt.Scale(scheme='category10')
                color_scale = alt.Color("Gene_Region:N", scale=scale)
                gene_region_selection = alt.selection_point(fields=['Gene_Region'], on='click')
                
                if calc_pvalue:
                    chart = alt.Chart(source).mark_circle().encode(
                        x=alt.X('Rel Position:Q', axis=alt.Axis(title='Relative position (bp)'), sort='ascending'),
                        y=alt.Y('Rel Score:Q', axis=alt.Axis(title='Relative Score'), scale=alt.Scale(domain=[ystart, ystop])),
                        color=alt.condition(gene_region_selection, color_scale, alt.value('lightgray')),
                        tooltip=['Rel Position', 'Rel Score', 'p-value', 'Sequence', 'Gene', 'Region']
                    ).properties(width=600, height=400).interactive().add_params(gene_region_selection)
                    
                    st.markdown('**Graph**',help='Zoom +/- with the mouse wheel. Drag while pressing the mouse to move the graph. Selection of a group by clicking on a point of the graph (double click de-selection). Double-click on a point to reset the zoom and the moving of graph.')
                    st.altair_chart(chart, theme=None, use_container_width=True)
                else:
                    chart = alt.Chart(source).mark_circle().encode(
                        x=alt.X('Rel Position:Q', axis=alt.Axis(title='Relative position (bp)'), sort='ascending'),
                        y=alt.Y('Rel Score:Q', axis=alt.Axis(title='Relative Score'), scale=alt.Scale(domain=[ystart, ystop])),
                        color=alt.condition(gene_region_selection, color_scale, alt.value('lightgray')),
                        tooltip=['Rel Position', 'Rel Score', 'Sequence', 'Gene', 'Region']
                    ).properties(width=600, height=400).interactive().add_params(gene_region_selection)
                    
                    st.markdown('**Graph**',help='Zoom +/- with the mouse wheel. Drag while pressing the mouse to move the graph. Selection of a group by clicking on a point of the graph (double click de-selection). Double-click on a point to reset the zoom and the moving of graph.')
                    st.altair_chart(chart, theme=None, use_container_width=True)
                    
                email_sender = st.secrets['sender']
                with colres4:
                    email_receiver = st.text_input('Send results by email ✉', value='Send results by email ✉', label_visibility='collapsed')
                subject = f'Results TFinder - {current_date_time}'
                body = f"Hello ☺\n\nResults obtained with TFinder.\n\nJASPAR_ID: {jaspar_id} | Transcription Factor name: {TF_name}\n\nRelScore Threshold:\n{threshold_entry}\n\nThis email also includes the sequences used in FASTA format and an Excel table of results.\n\nFor all requests/information, please refer to the 'Contact' tab on the TFinder website. We would be happy to answer all your questions.\n\nBest regards\nTFinder Team"
                password = st.secrets['password']
                attachment_excel = excel_file
                attachment_text = txt_output
                
                with colres4:
                    if st.button("Send ✉"):
                        try:
                            msg = MIMEMultipart()
                            msg['From'] = email_sender
                            msg['To'] = email_receiver
                            msg['Subject'] = subject

                            msg.attach(MIMEText(body, 'plain'))

                            attachment_excel = MIMEBase('application', 'octet-stream')
                            attachment_excel.set_payload(excel_file.getvalue())
                            encoders.encode_base64(attachment_excel)
                            attachment_excel.add_header('Content-Disposition', 'attachment', filename=f'Results_TFinder_{current_date_time}.xlsx')
                            msg.attach(attachment_excel)

                            attachment_text = MIMEText(attachment_text, 'plain', 'utf-8')
                            attachment_text.add_header('Content-Disposition', 'attachment', filename=f'Sequences_{current_date_time}.txt')
                            msg.attach(attachment_text)

                            server = smtplib.SMTP('smtp.gmail.com', 587)
                            server.starttls()
                            server.login(email_sender, password)
                            server.sendmail(email_sender, email_receiver, msg.as_string())
                            server.quit()
                            with colres5:
                                st.success('Email sent successfully! 🚀')
                        except smtplib.SMTPAuthenticationError:
                            with colres5:
                                st.error("Failed to authenticate. Please check your email and password.")
                        except smtplib.SMTPServerDisconnected:
                            with colres5:
                                st.error("Failed to connect to the SMTP server. Please check your internet connection.")
                        except smtplib.SMTPRecipientsRefused:
                            with colres5:
                                st.error(f"Error sending email: {email_receiver}")
                        except smtplib.SMTPException as e:
                            with colres5:
                                st.error(f"Error sending email: {e}")
                        except Exception as e:
                            with colres5:
                                st.error(f"Unknown error occurred: {e}")
                                
            else: 
                jaspar_id = sequence_consensus_input
                url = f"https://jaspar.genereg.net/api/v1/matrix/{jaspar_id}/"
                response = requests.get(url)
                response_data = response.json()
                TF_name = response_data['name']
                st.error(f"No consensus sequence found with the specified threshold for {TF_name}")
                
    else:
        if 'table2' in locals():
            if len(table2) > 0:
                current_date_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                st.subheader(':orange[Results]')
                colres1,colres2,colres3, colres4, colres5 = st.columns([1,0.5,0.5,1,1])
                with colres1:
                    st.success(f"Finding responsive elements done")
                df = pd.DataFrame(table2[1:], columns=table2[0])
                st.session_state['df'] = df
                st.markdown('**Table**')
                st.dataframe(df, hide_index=True)
                with colres2:
                    excel_file = io.BytesIO()
                    df.to_excel(excel_file, index=False, sheet_name='Sheet1')
                    excel_file.seek(0)
                    st.download_button("💾 Download table (.xls)", excel_file, file_name=f'Results_TFinder_{current_date_time}.xlsx', mime="application/vnd.ms-excel", key='download-excel')
                with colres3:
                    if jaspar == 'PWM':
                        if matrix_type == 'With PWM':
                            txt_output = f"Position Weight Matrix:\n{matrix_text}\n\nRelScore Threshold:\n{threshold_entry}\n\nSequences:\n{result_promoter}"
                        if matrix_type == 'With FASTA sequences':
                            txt_output = f"Responsive Elements:\n{fasta_text}\n\nPosition Weight Matrix:\n{matrix_text}\n\nRelScore Threshold:\n{threshold_entry}\n\nSequences:\n{result_promoter}"
                    else:
                        txt_output = f"Responsive Elements:\n{IUPAC}\n\nPosition Weight Matrix:\n{matrix_text}\n\nRelScore Threshold:\n{threshold_entry}\n\nSequences:\n{result_promoter}"
                    st.download_button(label="💾 Download sequences (.txt)",data=txt_output,file_name=f"Sequences_{current_date_time}.txt",mime="text/plain")
             
                source = df
                score_range = source['Rel Score'].astype(float)
                ystart = score_range.min() - 0.02
                ystop = score_range.max() + 0.02
                source['Gene_Region'] = source['Gene'] + " " + source['Region']
                scale = alt.Scale(scheme='category10')
                color_scale = alt.Color("Gene_Region:N", scale=scale)
                gene_region_selection = alt.selection_point(fields=['Gene_Region'], on='click')
                
                if calc_pvalue:
                    chart = alt.Chart(source).mark_circle().encode(
                        x=alt.X('Rel Position:Q', axis=alt.Axis(title='Relative position (bp)'), sort='ascending'),
                        y=alt.Y('Rel Score:Q', axis=alt.Axis(title='Relative Score'), scale=alt.Scale(domain=[ystart, ystop])),
                        color=alt.condition(gene_region_selection, color_scale, alt.value('lightgray')),
                        tooltip=['Rel Position', 'Rel Score', 'p-value', 'Sequence', 'Gene', 'Region']
                    ).properties(width=600, height=400).interactive().add_params(gene_region_selection)
                    
                    st.markdown('**Graph**',help='Zoom +/- with the mouse wheel. Drag while pressing the mouse to move the graph. Selection of a group by clicking on a point of the graph (double click de-selection). Double-click on a point to reset the zoom and the moving of graph.')
                    st.altair_chart(chart, theme=None, use_container_width=True)
                else:
                    chart = alt.Chart(source).mark_circle().encode(
                        x=alt.X('Rel Position:Q', axis=alt.Axis(title='Relative position (bp)'), sort='ascending'),
                        y=alt.Y('Rel Score:Q', axis=alt.Axis(title='Relative Score'), scale=alt.Scale(domain=[ystart, ystop])),
                        color=alt.condition(gene_region_selection, color_scale, alt.value('lightgray')),
                        tooltip=['Rel Position', 'Rel Score', 'Sequence', 'Gene', 'Region']
                    ).properties(width=600, height=400).interactive().add_params(gene_region_selection)
                    
                    st.markdown('**Graph**',help='Zoom +/- with the mouse wheel. Drag while pressing the mouse to move the graph. Selection of a group by clicking on a point of the graph (double click de-selection). Double-click on a point to reset the zoom and the moving of graph.')
                    st.altair_chart(chart, theme=None, use_container_width=True)
                    
                    
                email_sender = st.secrets['sender']
                with colres4:
                    email_receiver = st.text_input('Send results by email ✉', value='Send results by email ✉', label_visibility='collapsed')
                subject = f'Results TFinder - {current_date_time}'
                if jaspar == 'PWM':
                    if matrix_type == 'With PWM':
                        body = f"Hello ☺\n\nResults obtained with TFinder.\n\nPosition Weight Matrix:\n{matrix_text}\n\nRelScore Threshold:\n{threshold_entry}\n\nThis email also includes the sequences used in FASTA format and an Excel table of results.\n\nFor all requests/information, please refer to the 'Contact' tab on the TFinder website. We would be happy to answer all your questions.\n\nBest regards\nTFinder Team"
                    if matrix_type == 'With FASTA sequences':
                        body = f"Hello ☺\n\nResults obtained with TFinder.\n\nResponsive Elements:\n{fasta_text}\n\nPosition Weight Matrix:\n{matrix_text}\n\nRelScore Threshold:\n{threshold_entry}\n\nThis email also includes the sequences used in FASTA format and an Excel table of results.\n\nFor all requests/information, please refer to the 'Contact' tab on the TFinder website. We would be happy to answer all your questions.\n\nBest regards\nTFinder Team"
                else:
                    body = f"Hello ☺\n\nResults obtained with TFinder.\n\nResponsive Elements:\n{IUPAC}\n\nPosition Weight Matrix:\n{matrix_text}\n\nRelScore Threshold:\n{threshold_entry}\n\nThis email also includes the sequences used in FASTA format and an Excel table of results.\n\nFor all requests/information, please refer to the 'Contact' tab on the TFinder website. We would be happy to answer all your questions.\n\nBest regards\nTFinder Team"
                    
                password = st.secrets['password']
                attachment_excel = excel_file
                attachment_text = txt_output
                
                with colres4:
                    if st.button("Send ✉"):
                        try:
                            msg = MIMEMultipart()
                            msg['From'] = email_sender
                            msg['To'] = email_receiver
                            msg['Subject'] = subject

                            msg.attach(MIMEText(body, 'plain'))

                            attachment_excel = MIMEBase('application', 'octet-stream')
                            attachment_excel.set_payload(excel_file.getvalue())
                            encoders.encode_base64(attachment_excel)
                            attachment_excel.add_header('Content-Disposition', 'attachment', filename=f'Results_TFinder_{current_date_time}.xlsx')
                            msg.attach(attachment_excel)

                            attachment_text = MIMEText(attachment_text, 'plain', 'utf-8')
                            attachment_text.add_header('Content-Disposition', 'attachment', filename=f'Sequences_{current_date_time}.txt')
                            msg.attach(attachment_text)
                            
                            if jaspar == 'PWM':
                                if matrix_type == 'With FASTA sequences':
                                    image = MIMEImage(buffer.read(), name=f'LOGOMAKER_{current_date_time}.jpg')
                                    msg.attach(image)
                            elif jaspar == 'Manual sequence':
                                image = MIMEImage(buffer.read(), name=f'LOGOMAKER_{current_date_time}.jpg')
                                msg.attach(image)

                            server = smtplib.SMTP('smtp.gmail.com', 587)
                            server.starttls()
                            server.login(email_sender, password)
                            server.sendmail(email_sender, email_receiver, msg.as_string())
                            server.quit()
                            
                            with colres5:
                                st.success('Email sent successfully! 🚀')
                        except smtplib.SMTPAuthenticationError:
                            with colres5:
                                st.error("Failed to authenticate. Please check your email and password.")
                        except smtplib.SMTPServerDisconnected:
                            with colres5:
                                st.error("Failed to connect to the SMTP server. Please check your internet connection.")
                        except smtplib.SMTPRecipientsRefused:
                            with colres5:
                                st.error(f"Error sending email: {email_receiver}")
                        except smtplib.SMTPException as e:
                            with colres5:
                                st.error(f"Error sending email: {e}")
                        except Exception as e:
                            with colres5:
                                st.error(f"Unknown error occurred: {e}")
            else:
                st.error(f"No consensus sequence found with the specified threshold")