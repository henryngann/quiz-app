from anytree import Node, RenderTree, PreOrderIter
from anytree.exporter import DotExporter
from lib.Sentence import Sentence
from lib.Question import Question
from lib.Quizlet import Quizlet

class Document:
    PIXEL_TOL_RANGE = 30
    def __init__(self, paragraph_list):
        """
        Creates a tree structure that outlines the nested structure of the document
        TODO:
            * Rotate image so that the text can be aligned before sending it to the vision api
        """
        self.root_node = Node('root')
        self.annotation_list = []

        # Removes paragraphs that only contain 1 character
        paragraph_list = [paragraph for paragraph in paragraph_list if len(paragraph[0]) > 1]
        layer_num = 1
        parent_nodes = [self.root_node]
        prev_layer_list = []
        prev_top_left_x_val = 0

        while paragraph_list:
            top_left_idx = Document.find_top_left(paragraph_list)
            top_left_x_val = paragraph_list[top_left_idx][1].vertices[0].x 

            # If next top left value is extremely far away from the previous top left value, 
            # break loop and set remaining values as annotations
            if top_left_x_val > prev_top_left_x_val + (Document.PIXEL_TOL_RANGE*5):
                self.annotation_list = paragraph_list
                break

            layer_list = Document.find_nodes_in_same_layer(paragraph_list, top_left_x_val)
            parent_node_idx_list = self.determine_parent_node(layer_list, prev_layer_list)

            # Add to child nodes to the previous layer
            if parent_nodes != []:
                new_parent_nodes = []
                for i, paragraph in enumerate(layer_list):
                    sentenceList = Sentence.seperate_sentences(layer_list[i][0])
                    sentenceList = Sentence.update_subject(sentenceList)
                    questions = [Question(sentenceList) for sentenceList in sentenceList if Question.is_question(sentenceList)]
                    child_node = Node("layer: %s, child_num: %s" % (layer_num, i), parent=parent_nodes[parent_node_idx_list[i]], sentences=sentenceList, questions=questions, text=layer_list[i][0])
                    new_parent_nodes.append(child_node)

                # Update parent nodes list:
                parent_nodes = new_parent_nodes
                prev_layer_list = layer_list
                prev_top_left_x_val = top_left_x_val
                layer_num += 1
            else:
                paragraph_list = []

    @staticmethod
    def find_top_left(paragraph_list):
        """
        Top left node is defined as the left most paragraph within the first 5
        paragraphs
        """
        x_val_list = [paragraph_list[0][1].vertices[0].x for paragraph in paragraph_list[:5]]
        min_x = min(x_val_list)
        return x_val_list.index(min_x)

    @staticmethod
    def find_nodes_in_same_layer(paragraph_list, top_left_x_val):
        """
        Finds nodes in the same layer based on the x_value of the paragraph of the
        bounded box
        """
        top_layer_list = [] 
        remove_idx_list = []
        prev_x = top_left_x_val
        for idx, paragraph in enumerate(paragraph_list):
            x_val = paragraph[1].vertices[0].x
            if prev_x - Document.PIXEL_TOL_RANGE <= x_val <= prev_x + Document.PIXEL_TOL_RANGE:
                prev_x = x_val
                top_layer_list.append(paragraph_list[idx])
                remove_idx_list.append(idx)
        # Removing extra indices that are added to layer list
        for index in sorted(remove_idx_list, reverse=True):
            del paragraph_list[index]
        return top_layer_list

    def determine_parent_node(self, layer_list, prev_layer_list):
        """
        Returns indices of the layer on top of the current layer
        """
        parent_node_idx_list = []

        if prev_layer_list == []:
            return [0 for i in layer_list]

        prev_layer_y_list = [ paragraph[1].vertices[0].y for paragraph in prev_layer_list ]
        layer_y_list = [ paragraph[1].vertices[0].y for paragraph in layer_list ]

        remove_idx_list = []
        for idx, y in enumerate(layer_y_list):
            # Finds first index of parent node
            parent_idx = [i for i, val in enumerate(prev_layer_y_list) if y > val]

            # If there exists a node below a parent node, add the index to the list
            # otherwise, pop the index from the layer_list
            if parent_idx != []:
                parent_node_idx_list.append(parent_idx[-1])
            else:
                remove_idx_list.append(idx)
        
        # Removing extra indices that can't be matched with a parent node
        for index in sorted(remove_idx_list, reverse=True):
            del layer_list[index]

        return parent_node_idx_list

    def create_questions(self):
        prev_node = self.root_node
        node_iter = PreOrderIter(prev_node)
        question_list = []

        terms = []
        definitions = []

        for node in node_iter:
            # check if question is empty in node

            if node == self.root_node:
                continue

            question_starter = ''
            if len(node.ancestors) > 1:
                question_starter = 'For %s;\n\n' % ';'.join([ parent.text for parent in node.ancestors if parent != self.root_node])
                # checks if prev node is not a sibling 
                # creates a property question
                if prev_node is node.parent:
                    node_layer = [sibling for sibling in node.siblings]
                    node_layer.append(node)

                    temp_term = "%sWhat are the %s properties?" % (question_starter, len(node_layer))
                    temp_definition = '\n'.join([ "%s. " % (i+1) + sibling.text for i, sibling in enumerate(node_layer) ])
                    terms.append(temp_term)
                    definitions.append(temp_definition)

            prev_node = node
            if node.questions == []:
                continue
            
            temp_terms = [ question_starter + question.sentence.return_string() for question in node.questions]
            temp_definitions = [str(question.answer.content) for question in node.questions]

            # extend the question list
            terms.extend(temp_terms)
            definitions.extend(temp_definitions)


        quizlet_client = Quizlet(terms, definitions)
        return quizlet_client.create_set("My Set Title")

    def print(self):
        DotExporter(self.root_node).to_picture("test.png")
        print(RenderTree(self.root_node))






