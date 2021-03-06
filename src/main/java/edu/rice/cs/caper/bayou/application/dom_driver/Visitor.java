/*
Copyright 2017 Rice University

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/
package edu.rice.cs.caper.bayou.application.dom_driver;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import edu.rice.cs.caper.bayou.core.dsl.DASTNode;
import edu.rice.cs.caper.bayou.core.dsl.DSubTree;
import edu.rice.cs.caper.bayou.core.dsl.Sequence;
import org.apache.commons.lang3.tuple.ImmutablePair;
import org.apache.commons.lang3.tuple.Pair;
import org.eclipse.jdt.core.dom.*;

import java.io.FileNotFoundException;
import java.io.PrintWriter;
import java.util.*;
import java.util.stream.Collectors;

public class Visitor extends ASTVisitor {

    public final CompilationUnit unit;
    public final Options options;
    public final PrintWriter output;
    public final Gson gson;

    public List<MethodDeclaration> allMethods;

    private static Visitor V;

    public static Visitor V() {
        return V;
    }

    class JSONOutputWrapper {
        String file;
        DSubTree ast;
        List<Sequence> sequences;
        String javadoc;

        public JSONOutputWrapper(String file, DSubTree ast, List<Sequence> sequences, String javadoc) {
            this.file = file;
            this.ast = ast;
            this.sequences = sequences;
            this.javadoc = javadoc;
        }
    }

    public Visitor(CompilationUnit unit, Options options) throws FileNotFoundException {
        this.unit = unit;
        this.options = options;
        this.gson = new GsonBuilder().setPrettyPrinting().serializeNulls().create();

        if (options.cmdLine.hasOption("output-file"))
            this.output = new PrintWriter(options.cmdLine.getOptionValue("output-file"));
        else
            this.output = new PrintWriter(System.out);

        allMethods = new ArrayList<>();
        V = this;
    }

    @Override
    public boolean visit(TypeDeclaration clazz) {
        if (clazz.isInterface())
            return false;
        List<TypeDeclaration> classes = new ArrayList<>();
        classes.addAll(Arrays.asList(clazz.getTypes()));
        classes.add(clazz);

        for (TypeDeclaration cls : classes)
            allMethods.addAll(Arrays.asList(cls.getMethods()));
        List<MethodDeclaration> constructors = allMethods.stream().filter(m -> m.isConstructor()).collect(Collectors.toList());
        List<MethodDeclaration> publicMethods = allMethods.stream().filter(m -> !m.isConstructor() && Modifier.isPublic(m.getModifiers())).collect(Collectors.toList());

        Set<Pair<DSubTree, String>> astsWithJavadoc = new HashSet<>();
        if (!constructors.isEmpty() && !publicMethods.isEmpty()) {
            for (MethodDeclaration c : constructors)
                for (MethodDeclaration m : publicMethods) {
                    String javadoc = Utils.getJavadoc(m, options.JAVADOC_TYPE);
                    DSubTree ast = new DOMMethodDeclaration(c).handle();
                    ast.addNodes(new DOMMethodDeclaration(m).handle().getNodes());
                    if (ast.isValid())
                        astsWithJavadoc.add(new ImmutablePair<>(ast, javadoc));
                }
        } else if (!constructors.isEmpty()) { // no public methods, only constructor
            for (MethodDeclaration c : constructors) {
                String javadoc = Utils.getJavadoc(c, options.JAVADOC_TYPE);
                DSubTree ast = new DOMMethodDeclaration(c).handle();
                if (ast.isValid())
                    astsWithJavadoc.add(new ImmutablePair<>(ast, javadoc));
            }
        } else if (!publicMethods.isEmpty()) { // no constructors, methods executed typically through Android callbacks
            for (MethodDeclaration m : publicMethods) {
                String javadoc = Utils.getJavadoc(m, options.JAVADOC_TYPE);
                DSubTree ast = new DOMMethodDeclaration(m).handle();
                if (ast.isValid())
                    astsWithJavadoc.add(new ImmutablePair<>(ast, javadoc));
            }
        }

        for (Pair<DSubTree,String> astDoc : astsWithJavadoc) {
            List<Sequence> sequences = new ArrayList<>();
            sequences.add(new Sequence());
            try {
                astDoc.getLeft().updateSequences(sequences, options.MAX_SEQS, options.MAX_SEQ_LENGTH);
                List<Sequence> uniqSequences = new ArrayList<>(new HashSet<>(sequences));
                if (okToPrintAST(uniqSequences))
                    printJson(astDoc.getLeft(), uniqSequences, astDoc.getRight());
            } catch (DASTNode.TooManySequencesException e) {
                System.err.println("Too many sequences from AST");
            } catch (DASTNode.TooLongSequenceException e) {
                System.err.println("Too long sequence from AST");
            }
        }
        return false;
    }

    boolean first = true;
    private void printJson(DSubTree ast, List<Sequence> sequences, String javadoc) {
        String file = options.cmdLine.getOptionValue("input-file");
        JSONOutputWrapper out = new JSONOutputWrapper(file, ast, sequences, javadoc);
        output.write(first? "" : ",\n");
        output.write(gson.toJson(out));
        output.flush();
        first = false;
    }

    private boolean okToPrintAST(List<Sequence> sequences) {
        int n = sequences.size();
        if (n == 0 || (n == 1 && sequences.get(0).getCalls().size() <= 1))
            return false;
        return true;
    }

    public int getLineNumber(ASTNode node) {
        return unit.getLineNumber(node.getStartPosition());
    }
}
