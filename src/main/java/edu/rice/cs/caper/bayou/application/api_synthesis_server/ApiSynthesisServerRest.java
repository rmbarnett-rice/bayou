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
package edu.rice.cs.caper.bayou.application.api_synthesis_server;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.eclipse.jetty.server.Connector;
import org.eclipse.jetty.server.HttpConfiguration;
import org.eclipse.jetty.server.HttpConnectionFactory;
import org.eclipse.jetty.server.Server;
import org.eclipse.jetty.servlet.ServletHandler;

/**
 * Created by barnett on 6/5/17.
 */
class ApiSynthesisServerRest
{
    class StartErrorException extends Exception
    {
        StartErrorException(Throwable throwable)
        {
            super(throwable);
        }
    }

    /**
     * Place to send application logging information.
     */
    private static final Logger _logger = LogManager.getLogger(ApiSynthesisServerRest.class.getName());

    /**
     * The port on which to listen for incoming http connections.
     */
    private static final int _httpListenPort = Configuration.ListenPort;

    /**
     * That maximum supported size of the body of a HTTP code completion request.
     */
    private static int _codeCompletionRequestBodyMaxBytesCount = Configuration.CodeCompletionRequestBodyMaxBytesCount;

    void start() throws StartErrorException
    {
        /*
         * Create and configure the HTTP server.
         */
        Server server = new Server(_httpListenPort);
        {
            // Pattern as per https://www.eclipse.org/jetty/documentation/9.4.x/embedding-jetty.html
            ServletHandler handler = new ServletHandler();
            server.setHandler(handler);

            // register a servlet for performing apisynthesis
            handler.addServletWithMapping(ApiSynthesisServlet.class, "/apisynthesis");

            // register a servlet for collecting user feedback on result quatliy
            handler.addServletWithMapping(ApiSynthesisResultQualityFeedbackServlet.class, "/apisynthesisfeedback");

            // register a servlet for checking on the health of the entire apisynthesis process
            handler.addServletWithMapping(ApiSynthesisHealthCheckServlet.class, "/apisynthesishealth");

            /*
             * Code completion requests are sent via POST to CodeCompletionServletStartCompletion, however,
             * the site URL for the page that sends those POST requests can house that request body as a query parameter
             * for bookmarking.  That bookmarked URL then becomes the referrer of the POST request. As such there is a
             * relationship between the required header buffer size for this server and the allowed body size.
             *
             * As such ensure that we can accept headers as large as our max body size.
             */
            for (Connector c : server.getConnectors())
            {
                HttpConfiguration config = c.getConnectionFactory(HttpConnectionFactory.class).getHttpConfiguration();
                config.setRequestHeaderSize(_codeCompletionRequestBodyMaxBytesCount);
            }
        }

        /*
         * Start the HTTP server.
         */
        try
        {
            server.start();
            _logger.info("Started HTTP server on port " + _httpListenPort);
        }
        catch (Throwable e)
        {
            throw new StartErrorException(e);
        }
    }
}
